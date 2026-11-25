"""08 の補足。確認率(コスト)をそろえた比較と、個人の留保の持続性の検定。

A. 持続性: train で (ユーザー, 行為) に拒否があった組について、test での拒否数(観測 O)と、
   他ユーザーの同じ行為の拒否率から予想される拒否数(期待 E)を比べる。O/E > 1 なら、
   その人のその行為への拒否は、行為一般の危なさを超えて繰り返される。
B. 予算つき比較: test の全呼び出しをスコア順に並べ、上位 b%(確認率 = b)に入る拒否の割合(recall)。
   global   : 他ユーザーの行為別拒否率
   personal : 本人の train での行為別拒否率を global に縮約したもの (h + a*g)/(c + a), a=20
   fixed    : 常識リストを先に、残りは global 順
08 と同じ分割(ユーザーごとに前半/後半、4 セッション以上)。ブートストラップはユーザー単位 1000 回。
出力: data/derived/persistence{SUFFIX}.csv, data/derived/budget_recall{SUFFIX}.csv
"""
import os

import duckdb
import numpy as np
import pandas as pd

RNG = np.random.default_rng(20261121)
MIN_SESSIONS, ALPHA = 4, 20
BUDGETS = [0.01, 0.02, 0.05, 0.10, 0.20]
FIXED = {"git_commit", "git_push", "gh_pr_create", "gh_pr_merge", "gh_write", "publish",
         "deploy", "delete", "git_history"}

MODE = os.environ.get("PERM_MODES")  # 例: "default,acceptEdits"(指定時はその権限モードの呼び出しだけ)
ACOL = os.environ.get("ACTION_COL", "action")  # "action_c" で 12 の条件付き行為を使う
SRC = ("data/derived/tool_calls_cond.parquet" if ACOL != "action"
       else "data/derived/tool_calls_mode.parquet" if MODE else "data/derived/tool_calls.parquet")
MODE_SQL = (" and perm_mode in (" + ",".join(repr(m) for m in MODE.split(",")) + ")") if MODE else ""
SUFFIX = ("_" + MODE.replace(",", "_") if MODE else "") + ("_" + ACOL if ACOL != "action" else "")
base = duckdb.sql(f"""
  select user_id, session_id, {ACOL} as action, outcome <> 'ok' as hit, is_entireio, timestamp
  from '{SRC}' where action <> 'question'{MODE_SQL}""").df()


def prepare(df):
    df = df.join(df.groupby("session_id").timestamp.min().rename("s_start"), on="session_id")
    ses = df[["user_id", "session_id", "s_start"]].drop_duplicates()
    ses["n"] = ses.groupby("user_id").session_id.transform("size")
    ses = ses[ses.n >= MIN_SESSIONS].copy()
    ses["rank"] = ses.groupby("user_id").s_start.rank(method="first")
    ses["split"] = np.where(ses["rank"] <= ses.n / 2, "train", "test")
    return df.merge(ses[["session_id", "split"]], on="session_id")


def scored_test(df):
    """test の各呼び出しに global / personal スコアと、train での拒否の有無を付ける。"""
    tot = df.groupby("action").agg(c=("hit", "size"), h=("hit", "sum"))
    ua_all = df.groupby(["user_id", "action"]).agg(c=("hit", "size"), h=("hit", "sum"))
    ua_tr = df[df.split == "train"].groupby(["user_id", "action"]).agg(ct=("hit", "size"), ht=("hit", "sum"))
    test = df[df.split == "test"][["user_id", "action", "hit"]].copy()
    test = test.join(tot, on="action").join(ua_all, on=["user_id", "action"], rsuffix="_u")
    test = test.join(ua_tr, on=["user_id", "action"]).fillna({"ct": 0, "ht": 0})
    # leave-user-out の行為別拒否率
    test["g"] = ((test.h - test.h_u) / (test.c - test.c_u).replace(0, np.nan)).fillna(0)
    test["p"] = (test.ht + ALPHA * test.g) / (test.ct + ALPHA)
    test["f"] = test.action.str.split("|").str[0].isin(FIXED).astype(float) + test.g  # 固定リストを先頭に、残りは global 順
    test["train_hit"] = test.ht > 0
    # 統制: ユーザーの拒否しやすさ × 行為一般の拒否率(行為ごとの個人差を使わない)
    tr = df[df.split == "train"].groupby(["user_id", "action"]).agg(ct=("hit", "size"), ht=("hit", "sum"))
    tr = tr.join(tot, on="action").join(ua_all, on=["user_id", "action"], rsuffix="_u")
    tr["g"] = ((tr.h - tr.h_u) / (tr.c - tr.c_u).replace(0, np.nan)).fillna(0)
    tr["e"] = tr.ct * tr.g
    prop = tr.groupby("user_id").agg(O=("ht", "sum"), E=("e", "sum"))
    prop["r"] = (prop.O + 5 * 1.0) / (prop.E + 5 * 1.0)   # 弱い縮約(O/E の事前を 1 に)
    test = test.join(prop.r, on="user_id").fillna({"r": 1.0})
    test["u"] = test.g * test.r
    # スコアは (ユーザー, 行為) ごとに一定なので、組ごとに集約する(呼び出し数 n, 拒否数 hit)
    return (test.groupby(["user_id", "action"])
                .agg(n=("hit", "size"), hit=("hit", "sum"), g=("g", "first"), p=("p", "first"),
                     f=("f", "first"), u=("u", "first"), train_hit=("train_hit", "first"))
                .reset_index())


def persistence(test):
    out = {}
    for name, m in [("train_hit=yes", test.train_hit), ("train_hit=no", ~test.train_hit)]:
        t = test[m]
        out[name] = (t.hit.sum(), (t.g * t.n).sum(), t.n.sum())
    return out


def budget_recall(test):
    """組をスコア順に並べ、予算の境目にかかる組は按分する(同点内は呼び出しが一様に並ぶとみなす)。"""
    res = {}
    N, H = test.n.sum(), test.hit.sum()
    for col in ["g", "p", "f", "u"]:
        # 同スコアの組はまとめて按分する
        s = test.groupby(col)[["n", "hit"]].sum().sort_index(ascending=False)
        cn, ch = s.n.cumsum().values, s.hit.cumsum().values
        vals = []
        for b in BUDGETS:
            k = b * N
            i = np.searchsorted(cn, k)
            prev_n = cn[i - 1] if i > 0 else 0
            prev_h = ch[i - 1] if i > 0 else 0
            frac = (k - prev_n) / s.n.values[i]
            vals.append((prev_h + frac * s.hit.values[i]) / H)
        res[col] = vals
    return res


rows_p, rows_b = [], []
for label, filt in [("all", lambda d: d),
                    ("ex_entireio", lambda d: d[~d.is_entireio]),
                    ("ex_entireio_no_plan", lambda d: d[(~d.is_entireio) & (d.action != "plan_approval")])]:
    test = scored_test(prepare(filt(base)))
    users = test.user_id.unique()
    groups = {u: g for u, g in test.groupby("user_id")}
    boots_p, boots_b = [], []
    for _ in range(1000):
        s = pd.concat([groups[u] for u in RNG.choice(users, len(users), replace=True)])
        boots_p.append(persistence(s)); boots_b.append(budget_recall(s))
    pt, bt = persistence(test), budget_recall(test)
    for k, (O, E, n) in pt.items():
        r = np.array([b[k][0] / b[k][1] for b in boots_p if b[k][1] > 0])
        rows_p.append(dict(setting=label, group=k, test_calls=int(n), observed=int(O), expected=round(E, 1),
                           O_over_E=O / E, lo=np.percentile(r, 2.5), hi=np.percentile(r, 97.5)))
    for i, b in enumerate(BUDGETS):
        for col, name in [("g", "global"), ("p", "personal"), ("f", "fixed+global"), ("u", "user_prop")]:
            arr = np.array([bb[col][i] for bb in boots_b])
            rows_b.append(dict(setting=label, ask_rate=b, method=name, recall=bt[col][i],
                               lo=np.percentile(arr, 2.5), hi=np.percentile(arr, 97.5)))
        for other in ["g", "u"]:
            d = np.array([bb["p"][i] - bb[other][i] for bb in boots_b])
            nm = {"g": "personal-global", "u": "personal-user_prop"}[other]
            rows_b.append(dict(setting=label, ask_rate=b, method=nm, recall=bt["p"][i] - bt[other][i],
                               lo=np.percentile(d, 2.5), hi=np.percentile(d, 97.5)))

P, B = pd.DataFrame(rows_p), pd.DataFrame(rows_b)
P.to_csv(f"data/derived/persistence{SUFFIX}.csv", index=False)
B.to_csv(f"data/derived/budget_recall{SUFFIX}.csv", index=False)
pd.set_option("display.width", 200)
print("== A. 持続性(O/E)")
print(P.round(3).to_string(index=False), "\n")
print("== B. 確認率をそろえた recall")
B["ci"] = B.apply(lambda r: f"{r.recall:.3f} [{r.lo:.3f}, {r.hi:.3f}]", axis=1)
print(B.pivot_table(index=["setting", "ask_rate"], columns="method", values="ci", aggfunc="first").to_string())
