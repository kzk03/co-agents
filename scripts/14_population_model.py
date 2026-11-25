"""母集団レベルで、拒否の起きやすさを条件で説明する(RQ1: 人に残す判断の基準)。

ロジスティック回帰(GLM binomial)、ユーザー単位のクラスタ頑健標準誤差。
  hit ~ action_group + consequential:unrequested + depth + perm_mode
対象: entireio/cli 以外。計画承認・質問(もともと人に確認する仕組み)を除く。
  action_group : 重い行為は行為名、それ以外は read / read_only / file_edit / run / test_build / other に集約
  unreq        : 重い行為(12 の CONSEQUENTIAL)で、直前の発話に頼む語が無い
  perm_mode    : 不明も 1 水準として入れる
時間方向の頑健性: 前半(各呼び出しの時刻が全体の中央値より前)で推定し、後半での予測の当たり(AUC)も出す。
出力: data/derived/population_model.csv
"""
import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

CONSEQ = ["git_commit", "git_push", "gh_pr_create", "gh_pr_merge", "gh_write", "deploy", "publish",
          "delete", "git_history", "git_add", "pkg_install"]
df = duckdb.sql("""
  select user_id, action, requested, depth, coalesce(perm_mode, 'unknown') perm_mode,
         (outcome <> 'ok')::int hit, timestamp
  from 'data/derived/tool_calls_cond.parquet'
  where not is_entireio and action not in ('plan_approval', 'question')""").df()
keep = set(CONSEQ) | {"read", "read_only", "file_edit", "run", "test_build", "subagent", "git_read", "network"}
df["ag"] = np.where(df.action.isin(keep), df.action, "other")
df["ag"] = df.ag.replace({"publish": "deploy"})  # publish は拒否 0 件なので deploy にまとめる
df["unreq"] = (df.action.isin(CONSEQ) & ~df.requested.fillna(True).astype(bool)).astype(int)
df["depth"] = pd.Categorical(df.depth, ["1-5", "6-30", "31+"])
n0 = len(df)
df = df.dropna(subset=["user_id", "depth"]).reset_index(drop=True)
print(f"欠損で除外: {n0 - len(df)} 行")

formula = "hit ~ C(ag, Treatment('read_only')) + unreq + C(depth) + C(perm_mode, Treatment('default'))"


def fit(d):
    groups = pd.factorize(d.user_id)[0]
    return smf.glm(formula, d, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": groups})


m = fit(df)
tab = pd.DataFrame({"coef": m.params, "OR": np.exp(m.params), "lo": np.exp(m.conf_int()[0]),
                    "hi": np.exp(m.conf_int()[1]), "p": m.pvalues}).round(4)
tab.to_csv("data/derived/population_model.csv")
pd.set_option("display.width", 200)
print(f"n={len(df)}  hits={df.hit.sum()}  users={df.user_id.nunique()}")
print(tab.to_string())

# 時間方向: 前半で推定 → 後半で AUC
cut = df.timestamp.median()
tr, te = df[df.timestamp <= cut], df[df.timestamp > cut].copy()
# 前半に無い水準(例: auto モードは後半にしか無い)は unknown / other に寄せる
te.loc[~te.perm_mode.isin(tr.perm_mode.unique()), "perm_mode"] = "unknown"
te.loc[~te.ag.isin(tr.ag.unique()), "ag"] = "other"
print(f"前半: {tr.timestamp.min()} 〜 {cut} / 後半の auto など未知モード → unknown")
mt = fit(tr)
p = mt.predict(te)
def auc(y, s):
    r = pd.Series(s).rank().values
    n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
y = te.hit.values
print(f"\n前半で推定 → 後半の AUC = {auc(y, p.values):.3f}  (後半 n={len(te)}, hits={y.sum()})")
m2 = smf.glm("hit ~ C(perm_mode, Treatment('default'))", tr, family=sm.families.Binomial()).fit()
print(f"  比較: 権限モードだけのモデル AUC = {auc(y, m2.predict(te).values):.3f}")
mt_unreq = mt.params.get("unreq")
print(f"  前半推定での unreq の OR = {np.exp(mt_unreq):.2f}")
