"""留保候補の操作的定義を、その後の行動で検証する(RQ3 の予備実験)。

ユーザーごとにセッションを開始時刻順に並べ、前半(train)/後半(test)に分ける。
  personal(K) : train で K セッション以上 拒否・中断された行為の集合 = そのユーザーの Human.md
  global      : 他ユーザー(全期間)で拒否率の高い行為を、personal と同じ個数だけ
  fixed       : 常識的な固定リスト(commit/push/PR/公開/デプロイ/削除/履歴操作)
  random      : 行為を無作為に personal と同じ個数(乱数の種固定、20 回平均)
指標(test 期間、マイクロ平均):
  recall    = リストに入る行為への拒否 / 全拒否
  ask_rate  = リストに入る行為の呼び出し / 全呼び出し(人に聞く頻度 = コスト)
  lift      = (リスト内の拒否率) / (全体の拒否率)
信頼区間はユーザー単位のブートストラップ(1000 回)。
出力: data/derived/temporal_validation.csv
"""
import duckdb
import numpy as np
import pandas as pd

RNG = np.random.default_rng(20261121)
MIN_SESSIONS = 4
FIXED = {"git_commit", "git_push", "gh_pr_create", "gh_pr_merge", "gh_write", "publish",
         "deploy", "delete", "git_history"}

base = duckdb.sql("""
  select user_id, session_id, action, outcome <> 'ok' as hit, is_entireio, timestamp
  from 'data/derived/tool_calls.parquet' where action <> 'question'""").df()


def prepare(df):
    start = df.groupby("session_id").timestamp.min().rename("s_start")
    df = df.join(start, on="session_id")
    ses = df[["user_id", "session_id", "s_start"]].drop_duplicates()
    ses["n"] = ses.groupby("user_id").session_id.transform("size")
    ses = ses[ses.n >= MIN_SESSIONS].copy()
    ses["rank"] = ses.groupby("user_id").s_start.rank(method="first")
    ses["split"] = np.where(ses["rank"] <= ses.n / 2, "train", "test")
    return df.merge(ses[["session_id", "split"]], on="session_id")


def lists_for_user(u, train_u, rate_others, all_actions, k):
    sess_per_action = train_u[train_u.hit].groupby("action").session_id.nunique()
    personal = set(sess_per_action[sess_per_action >= k].index)
    n = len(personal)
    glob = set(rate_others.drop(index=list(rate_others.index.difference(all_actions)), errors="ignore")
               .sort_values(ascending=False).index[:n])
    return personal, glob


def evaluate(df, label, k):
    train, test = df[df.split == "train"], df[df.split == "test"]
    all_actions = sorted(df.action.unique())
    # 他ユーザーの拒否率(leave-user-out): 全体から本人分を引く
    tot = df.groupby("action").agg(c=("hit", "size"), h=("hit", "sum"))
    per_user = df.groupby(["user_id", "action"]).agg(c=("hit", "size"), h=("hit", "sum"))
    rows = []
    for u, test_u in test.groupby("user_id"):
        train_u = train[train.user_id == u]
        if not train_u.hit.any() or not test_u.hit.any():
            continue  # train で拒否が無い人は Human.md が空 / test に拒否が無い人は recall が定義できない
        mine = per_user.loc[u].reindex(tot.index, fill_value=0)
        others = tot - mine
        rate_others = (others.h / others.c.replace(0, np.nan)).dropna()
        personal, glob = lists_for_user(u, train_u, rate_others, all_actions, k)
        if not personal:
            continue
        acts = test_u.action.values
        hits = test_u.hit.values
        def stats(S):
            m = np.isin(acts, list(S))
            return m.sum(), hits[m].sum()
        r = dict(user_id=u, calls=len(acts), hits=hits.sum(), n_list=len(personal))
        for name, S in [("personal", personal), ("global", glob), ("fixed", FIXED)]:
            r[f"{name}_flag"], r[f"{name}_hit"] = stats(S)
        rf, rh = [], []
        for _ in range(20):
            S = set(RNG.choice(all_actions, size=len(personal), replace=False))
            f, h = stats(S); rf.append(f); rh.append(h)
        r["random_flag"], r["random_hit"] = np.mean(rf), np.mean(rh)
        rows.append(r)
    per = pd.DataFrame(rows)

    def micro(p):
        out = {}
        base_rate = p.hits.sum() / p.calls.sum()
        for name in ["personal", "global", "fixed", "random"]:
            rec = p[f"{name}_hit"].sum() / p.hits.sum()
            ask = p[f"{name}_flag"].sum() / p.calls.sum()
            prec = p[f"{name}_hit"].sum() / max(p[f"{name}_flag"].sum(), 1)
            out[name] = (rec, ask, prec / base_rate)
        return out

    point = micro(per)
    boots = [micro(per.sample(len(per), replace=True, random_state=int(RNG.integers(1e9)))) for _ in range(1000)]
    res = []
    for name in ["personal", "global", "fixed", "random"]:
        arr = np.array([b[name] for b in boots])
        lo, hi = np.percentile(arr, [2.5, 97.5], axis=0)
        res.append(dict(setting=label, K=k, method=name, users=len(per),
                        test_calls=int(per.calls.sum()), test_hits=int(per.hits.sum()),
                        mean_list_size=round(per.n_list.mean(), 2),
                        recall=point[name][0], recall_lo=lo[0], recall_hi=hi[0],
                        ask_rate=point[name][1], lift=point[name][2], lift_lo=lo[2], lift_hi=hi[2]))
    # personal と global の差(recall)のブートストラップ
    d = np.array([b["personal"][0] - b["global"][0] for b in boots])
    res.append(dict(setting=label, K=k, method="personal-global(recall diff)", users=len(per),
                    recall=point["personal"][0] - point["global"][0],
                    recall_lo=np.percentile(d, 2.5), recall_hi=np.percentile(d, 97.5)))
    return res


out = []
for label, filt in [("all", lambda d: d),
                    ("ex_entireio", lambda d: d[~d.is_entireio]),
                    ("ex_entireio_no_plan", lambda d: d[(~d.is_entireio) & (d.action != "plan_approval")])]:
    df = prepare(filt(base))
    for k in (1, 2):
        out += evaluate(df, label, k)
res = pd.DataFrame(out)
res.to_csv("data/derived/temporal_validation.csv", index=False)
pd.set_option("display.width", 200)
fmt = res.copy()
for c in ["recall", "recall_lo", "recall_hi", "ask_rate", "lift", "lift_lo", "lift_hi"]:
    fmt[c] = fmt[c].map(lambda x: "" if pd.isna(x) else f"{x:.3f}")
print(fmt[["setting", "K", "method", "users", "test_hits", "mean_list_size", "recall", "recall_lo",
           "recall_hi", "ask_rate", "lift", "lift_lo", "lift_hi"]].to_string(index=False))
