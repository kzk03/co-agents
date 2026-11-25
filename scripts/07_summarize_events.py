"""06 の tool_calls から、行為ごとの拒否・中断と、ユーザー単位の繰り返しを集計する。

留保候補の操作的定義:
  同じユーザーが同じ行為(action)を、異なる K セッション以上で拒否・中断した組。
拒否率の分母は 2 通り出す:
  all       : 全ツール呼び出し(自動承認のモードも含むので過小になる)
  prompting : 一度でも拒否したことのあるユーザー(= 確認を出す設定で使っている人)に限る
出力: data/derived/summary_actions.csv, summary_reserve_candidates.csv
"""
import duckdb

K = 2
con = duckdb.connect()
con.sql("create view t as select *, outcome <> 'ok' as hit from 'data/derived/tool_calls.parquet'")
con.sql("create view prompting as select distinct user_id from t where hit")

def actions(where):
    return con.sql(f"""
    select action,
           count(*) calls,
           count(*) filter (where outcome='rejected') rejected,
           count(*) filter (where outcome='interrupted') interrupted,
           round(1000.0 * count(*) filter (where hit) / count(*), 2) hit_per_mille_all,
           round(1000.0 * count(*) filter (where hit and user_id in (select * from prompting))
                 / nullif(count(*) filter (where user_id in (select * from prompting)), 0), 2) hit_per_mille_prompting,
           count(distinct user_id) filter (where hit) users_hit,
           round(100.0 * count(feedback) / nullif(count(*) filter (where outcome='rejected'), 0), 1) pct_with_feedback
    from t where {where}
    group by 1 order by (rejected + interrupted) desc""").df()

a_all, a_ex = actions("true"), actions("not is_entireio")
a = a_all.merge(a_ex, on="action", how="outer", suffixes=("", "_ex_entireio")).sort_values("rejected", ascending=False)
a.to_csv("data/derived/summary_actions.csv", index=False)

cand = con.sql(f"""
  select user_id, action, count(*) n_hits, count(distinct session_id) n_sessions,
         count(distinct repo_id) n_repos, bool_or(is_entireio) any_entireio,
         min(timestamp) first_ts, max(timestamp) last_ts
  from t where hit group by 1, 2 having count(distinct session_id) >= {K}
  order by n_sessions desc""").df()
cand.to_csv("data/derived/summary_reserve_candidates.csv", index=False)

print("== 全体")
print(con.sql("""select count(*) calls, count(*) filter (where hit) hits,
   count(distinct user_id) users, (select count(*) from prompting) prompting_users,
   count(distinct user_id) filter (where not is_entireio) users_ex,
   count(*) filter (where hit and not is_entireio) hits_ex from t""").df().to_string(), "\n")
cols = ["action", "calls", "rejected", "interrupted", "hit_per_mille_prompting", "users_hit",
        "pct_with_feedback", "rejected_ex_entireio", "users_hit_ex_entireio"]
print("== 行為ごと(上位 25)")
print(a[cols].head(25).to_string(index=False), "\n")
print(f"== 留保候補(同じユーザー × 行為で {K} セッション以上): {len(cand)} 組,",
      f"ユーザー {cand.user_id.nunique()} 人, entireio を除くと {len(cand[~cand.any_entireio])} 組")
print(cand.groupby("action").agg(pairs=("user_id", "size"), users=("user_id", "nunique"),
      med_sessions=("n_sessions", "median")).sort_values("pairs", ascending=False).head(20).to_string())
