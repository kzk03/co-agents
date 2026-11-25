"""パイロット用に 30 セッションを選ぶ。

母集団: Claude Code / 開始時点で定義ファイルあり / entireio/cli 以外 /
        通常セッション(kind 空)/ prompt_count >= 3 / conversations に行がある
1 リポジトリ・1 ユーザーにつき 1 件まで。乱数の種は固定。
出力: data/derived/pilot_sessions.csv
"""
import duckdb, pandas as pd
N, SEED = 30, 20261121
pop = duckdb.sql("""
  select d.session_id, d.repo_id, r.url, s.user_id, s.prompt_count, s.turn_count,
         s.duration_seconds, d.t, d.def_files, s.viewer_url_hf
  from 'data/derived/session_defs.parquet' d
  join 'data/swe-chat/sessions.parquet' s using(session_id)
  join 'data/swe-chat/repositories.parquet' r on r.repo_id = d.repo_id
  where d.n_def > 0 and s.agent = 'Claude Code' and r.url not like '%/entireio/cli'
    and coalesce(s.kind,'') = '' and s.prompt_count >= 3
    and d.session_id in (select distinct session_id
                         from 'data/swe-chat/conversations.parquet')""").df()
pop = pop.sample(frac=1, random_state=SEED)
pick, repos, users = [], set(), set()
for r in pop.itertuples():
    if r.repo_id in repos or r.user_id in users: continue
    pick.append(r); repos.add(r.repo_id); users.add(r.user_id)
    if len(pick) == N: break
out = pd.DataFrame(pick).drop(columns="Index")
out.to_csv("data/derived/pilot_sessions.csv", index=False)
print(f"population={len(pop)}  picked={len(out)}")
print(out[["url", "prompt_count", "turn_count"]].to_string())
