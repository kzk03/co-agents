"""前半のデータから共通の Human.md(条件付きの規則)を作り、後半のデータで当たりを測る。

対象: entireio/cli 以外、計画承認・質問を除く(もともと人に確認する仕組み)。時刻の中央値で前半/後半に分ける。
規則の単位:
  cond   : 重い行為は (行為, 頼まれたか)、それ以外は 行為
  action : 行為だけ(条件なし)
選び方: 前半の拒否率の Wilson 下限 > 前半全体の拒否率 × RATIO の単位を「人に確認する」規則にする。
評価(後半): recall(拒否のうち規則に入る割合)、ask_rate(呼び出しのうち規則に入る割合)、lift。
確認率をそろえた比較: 前半の拒否率で単位を並べ、後半で予算 b までの recall(境目の単位は按分)。
ブートストラップは後半のユーザー単位 1000 回。
出力: docs/Human.common.md(規則の草案)、data/derived/common_humanmd_eval.csv
"""
import duckdb
import numpy as np
import pandas as pd

RATIO, Z = 2.0, 1.96
BUDGETS = [0.01, 0.02, 0.05, 0.10, 0.20]
RNG = np.random.default_rng(20261121)
CONSEQ_JA = {"git_commit": "commit", "git_push": "push", "gh_pr_create": "PR の作成", "gh_pr_merge": "PR のマージ",
             "gh_write": "GitHub への書き込み(issue・コメント・PR の編集など)", "deploy": "デプロイ",
             "publish": "公開(パッケージ・リリース)", "delete": "削除(rm・prune など)",
             "git_history": "履歴の操作(reset・rebase・checkout・stash など)", "git_add": "git add",
             "pkg_install": "依存の追加・削除"}

df = duckdb.sql("""
  select user_id, session_id, action, requested, (outcome <> 'ok') hit, timestamp
  from 'data/derived/tool_calls_cond.parquet'
  where not is_entireio and action not in ('plan_approval', 'question')""").df()
df["cond"] = np.where(df.requested.isna(), df.action,
                      df.action + np.where(df.requested.fillna(False).astype(bool), "|req", "|unreq"))
cut = df.timestamp.median()
tr, te = df[df.timestamp <= cut], df[df.timestamp > cut]
base_tr = tr.hit.mean()


def wilson_lo(h, n):
    p = h / n
    return (p + Z**2 / (2 * n) - Z * np.sqrt(p * (1 - p) / n + Z**2 / (4 * n**2))) / (1 + Z**2 / n)


def rules(unit):
    s = tr.groupby(unit).agg(n=("hit", "size"), h=("hit", "sum"))
    s["rate"] = s.h / s.n
    s["lo"] = wilson_lo(s.h, s.n)
    s["selected"] = s.lo > base_tr * RATIO
    return s.sort_values("rate", ascending=False)


def evaluate(t, unit, selected):
    m = t[unit].isin(selected)
    return t.hit[m].sum() / t.hit.sum(), m.mean()


def budget_curve(t, unit, order):
    s = t.groupby(unit).agg(n=("hit", "size"), h=("hit", "sum")).reindex(order).dropna()
    rest = t[~t[unit].isin(order)]
    s = pd.concat([s, pd.DataFrame({"n": [len(rest)], "h": [rest.hit.sum()]}, index=["(未知)"])])
    cn, ch = s.n.cumsum().values, s.h.cumsum().values
    N, H = len(t), t.hit.sum()
    out = []
    for b in BUDGETS:
        k = b * N
        i = min(np.searchsorted(cn, k), len(cn) - 1)
        pn, ph = (cn[i - 1], ch[i - 1]) if i > 0 else (0, 0)
        out.append((ph + (k - pn) / s.n.values[i] * s.h.values[i]) / H)
    return out


R = {u: rules(u) for u in ["cond", "action"]}
sel = {u: list(R[u].index[R[u].selected]) for u in R}
order = {u: list(R[u].index) for u in R}

groups = {u: g for u, g in te.groupby("user_id")}
users = list(groups)
point = {u: evaluate(te, u, sel[u]) for u in R}
curve = {u: budget_curve(te, u, order[u]) for u in R}
bs_sel, bs_curve = {u: [] for u in R}, {u: [] for u in R}
for _ in range(1000):
    s = pd.concat([groups[u] for u in RNG.choice(users, len(users), replace=True)])
    for u in R:
        bs_sel[u].append(evaluate(s, u, sel[u]))
        bs_curve[u].append(budget_curve(s, u, order[u]))

rows = []
for u in R:
    a = np.array(bs_sel[u])
    rows.append(dict(unit=u, kind="selected_rules", n_rules=len(sel[u]), recall=point[u][0],
                     recall_lo=np.percentile(a[:, 0], 2.5), recall_hi=np.percentile(a[:, 0], 97.5),
                     ask_rate=point[u][1], lift=point[u][0] / point[u][1]))
    c = np.array(bs_curve[u])
    for i, b in enumerate(BUDGETS):
        rows.append(dict(unit=u, kind=f"budget_{b}", recall=curve[u][i],
                         recall_lo=np.percentile(c[:, i], 2.5), recall_hi=np.percentile(c[:, i], 97.5), ask_rate=b))
d = np.array(bs_curve["cond"]) - np.array(bs_curve["action"])
for i, b in enumerate(BUDGETS):
    rows.append(dict(unit="cond-action", kind=f"budget_{b}", recall=curve["cond"][i] - curve["action"][i],
                     recall_lo=np.percentile(d[:, i], 2.5), recall_hi=np.percentile(d[:, i], 97.5), ask_rate=b))
E = pd.DataFrame(rows)
E.to_csv("data/derived/common_humanmd_eval.csv", index=False)

# ---- Human.md の草案(条件付きの単位から)----
te_s = te.groupby("cond").agg(n=("hit", "size"), h=("hit", "sum"))
ex = df[df.hit].groupby("cond").session_id.first()
lines = ["# Human.md(共通の草案。SWE-chat の拒否から自動生成)", "",
         f"- 作り方: {tr.timestamp.min():%Y-%m-%d}〜{cut:%Y-%m-%d} の Claude Code の呼び出し {len(tr):,} 件"
         f"(entireio/cli・計画承認・質問を除く)で、拒否率の 95% 下限が全体({base_tr*1000:.2f}‰)の {RATIO:g} 倍を超えた行為。",
         f"- 後半({cut:%Y-%m-%d}〜)での当たり: 拒否の {point['cond'][0]:.0%} がこの規則に入る。規則に入る呼び出しは全体の {point['cond'][1]:.1%}。",
         "", "| 何を | どんなときに | 誰が決めるか | どう確認するか | 根拠(前半の拒否率 / 後半の拒否率) |", "|---|---|---|---|---|"]
for k in sel["cond"]:
    act, _, c = k.partition("|")
    what = CONSEQ_JA.get(act, act)
    when = {"unreq": "直前の発話で頼まれていないとき", "req": "頼まれたとき(やり方の確認)"}.get(c, "常に")
    r, t2 = R["cond"].loc[k], te_s.loc[k] if k in te_s.index else None
    later = f"{t2.h / t2.n * 1000:.1f}‰ ({int(t2.h)}/{int(t2.n)})" if t2 is not None else "-"
    lines.append(f"| {what} | {when} | 人に聞く | 実行前に承認を得る | {r.rate*1000:.1f}‰ ({int(r.h)}/{int(r.n)}) / {later}; 例 `{ex.get(k, '')}` |")
lines += ["", "## 選ばれなかった重い行為(参考)", ""]
for k in R["cond"].index:
    if k in sel["cond"] or k.split("|")[0] not in CONSEQ_JA:
        continue
    r = R["cond"].loc[k]
    lines.append(f"- {k}: 前半 {r.rate*1000:.1f}‰ ({int(r.h)}/{int(r.n)})")
open("docs/Human.common.md", "w").write("\n".join(lines) + "\n")

pd.set_option("display.width", 200)
print(f"前半の全体拒否率 {base_tr*1000:.2f}‰ / 閾値(下限) {base_tr*RATIO*1000:.2f}‰")
print("選ばれた規則(cond):", sel["cond"])
print("選ばれた規則(action):", sel["action"])
print(E.round(3).to_string(index=False))
