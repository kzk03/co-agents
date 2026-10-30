"""repo の偏りに対する感度分析(aidev 100件 vs ghhuman 100件、多数決ラベル、BOT/UNK/NOAGREE 除外)。
推定法:
 (0) 既存: 結末層の重み(scripts/irr.py stats と同じ)
 (1) repo 上限 k(k=1,2): repo ごとに最大 k 件を無作為に残す × 500 回の平均(重みは結末層)
 (2) repo 等重み: 各 repo の合計重みを 1 にする(repo 内の H 率の平均)
 (3) 母集団 repo 重み: 重み = 母集団件数(結末層×repo)/ サンプル件数(結末層×repo)。サンプルに無い repo は無視
 (3b) 結末層×(home-assistant/core か否か)の重み(ghhuman のみ意味あり)
 区間はすべて repo クラスタ・ブートストラップ(群ごとに repo を復元抽出、2000 回、seed 0)
 (4) ロジスティック回帰 H ~ 群 + closed: (a) 通常 (b) repo クラスタ頑健 SE (c) GEE(交換可能、repo クラスタ)
     (d) repo 変量効果(statsmodels BinomialBayesMixedGLM, 変分ベイズ)
実行(humans_md/ で): uv run work/baseline/repo_sensitivity.py → work/baseline/repo_sensitivity.txt
"""
import collections, csv, json, os, random
import numpy as np, pandas as pd
import statsmodels.api as sm, statsmodels.formula.api as smf
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
out = []; P = lambda *a: out.append(" ".join(str(x) for x in a))
st = lambda o: "closed" if o == "closed" else "not_closed"

# 母集団
cr = pd.read_parquet(f"{ROOT}/outputs/aidev/human_blocks.parquet")
cr["repo"] = cr["html_url"].str.split("github.com/").str[1].str.split("/pull/").str[0]
popA = collections.Counter(zip(cr["outcome"].map(st), cr["repo"]))
gh = [json.loads(l) for l in open(f"{ROOT}/work/baseline/ghhuman_blocks.jsonl")]
popH = collections.Counter((st(r["outcome"]), r["repo"]) for r in gh if not r["agent_coauthor"])
POP = {"aidev": popA, "ghhuman": popH}

rows = []
for name in ["aidev", "ghhuman"]:
    m = {r["sid"]: r for r in csv.DictReader(open(f"{ROOT}/outputs/{name}/irr/irr_merged.csv"))}
    for s in json.load(open(f"{ROOT}/outputs/{name}/sample100.json")):
        mj = m[s["sid"]]["majority"]
        if mj in ("BOT", "UNK", "NOAGREE"):
            continue
        rows.append(dict(grp=name, sid=s["sid"], repo=s["repo"], st=s["stratum"], H=int(mj.startswith("H"))))
D = pd.DataFrame(rows)
P("== 有効件数と repo 数")
for g, d in D.groupby("grp"):
    vc = d["repo"].value_counts()
    P(f" {g}: n={len(d)} repo={d['repo'].nunique()} 1repoあたり最大 {vc.max()} 件、上位 {vc.head(5).to_dict()}")
    pr = collections.Counter(); [pr.update({k[1]: v}) for k, v in POP[g].items()]
    tot = sum(pr.values()); P(f"   母集団: CR {tot} repo {len(pr)} 最大 repo {pr.most_common(1)[0]} ({pr.most_common(1)[0][1] / tot:.3f})")


def w_strat(d, g):
    pop = collections.Counter(); [pop.update({k[0]: v}) for k, v in POP[g].items()]
    sc = d["st"].value_counts()
    return d["st"].map(lambda s: pop[s] / sc[s])


def w_repo_equal(d, g):
    n = d["repo"].value_counts(); return d["repo"].map(lambda r: 1 / n[r])


def w_pop_repo(d, g):
    sc = collections.Counter(zip(d["st"], d["repo"]))
    return pd.Series([POP[g][(s, r)] / sc[(s, r)] for s, r in zip(d["st"], d["repo"])], index=d.index)


def w_ha(d, g):
    pop = collections.Counter(); [pop.update({(k[0], k[1] == "home-assistant/core"): v}) for k, v in POP[g].items()]
    cell = list(zip(d["st"], d["repo"] == "home-assistant/core")); sc = collections.Counter(cell)
    return pd.Series([pop[c] / sc[c] for c in cell], index=d.index)


def share(d, g, wf):
    w = wf(d, g); return float((w * d["H"]).sum() / w.sum())


def cboot(wf, B=2000, seed=0):
    rng = random.Random(seed); res = {"aidev": [], "ghhuman": [], "diff": []}
    groups = {g: {r: d for r, d in D[D.grp == g].groupby("repo")} for g in ["aidev", "ghhuman"]}
    for _ in range(B):
        s = {}
        for g, rp in groups.items():
            keys = list(rp); pick = [rp[rng.choice(keys)] for _ in keys]
            d = pd.concat(pick, ignore_index=True)
            # 結末層が片方だけになったら層重みが定義できないので、その回は層を無視
            s[g] = share(d, g, wf)
            res[g].append(s[g])
        res["diff"].append(s["ghhuman"] - s["aidev"])
    q = lambda v: (np.percentile(v, 2.5), np.percentile(v, 97.5))
    return {k: q(v) for k, v in res.items()}


P("\n== 重み付き H 系比率(区間は repo クラスタ・ブートストラップ 2000 回)")
for lab, wf in [("(0) 結末層", w_strat), ("(2) repo 等重み", w_repo_equal), ("(3) 母集団 repo 重み", w_pop_repo),
                ("(3b) 結末層×HA", w_ha)]:
    pt = {g: share(D[D.grp == g], g, wf) for g in ["aidev", "ghhuman"]}
    ci = cboot(wf)
    P(f" {lab}: aidev {pt['aidev']:.3f} ({ci['aidev'][0]:.3f}-{ci['aidev'][1]:.3f})  ghhuman {pt['ghhuman']:.3f} "
      f"({ci['ghhuman'][0]:.3f}-{ci['ghhuman'][1]:.3f})  差 {pt['ghhuman'] - pt['aidev']:.3f} ({ci['diff'][0]:.3f}-{ci['diff'][1]:.3f})")

P("\n== (1) repo 上限 k(無作為に k 件残す×500 回、結末層の重み)。値は 500 回の平均と 2.5/97.5 パーセンタイル")
for k in [1, 2]:
    rng = random.Random(k); vals = collections.defaultdict(list)
    for _ in range(500):
        idx = [i for _, x in D.groupby(["grp", "repo"]) for i in rng.sample(list(x.index), min(len(x), k))]
        d = D.loc[idx]
        s = {g: share(d[d.grp == g], g, w_strat) for g in ["aidev", "ghhuman"]}
        vals["aidev"].append(s["aidev"]); vals["ghhuman"].append(s["ghhuman"]); vals["diff"].append(s["ghhuman"] - s["aidev"])
        vals["n_a"].append((d.grp == "aidev").sum()); vals["n_h"].append((d.grp == "ghhuman").sum())
    f = lambda v: f"{np.mean(v):.3f} [{np.percentile(v, 2.5):.3f}, {np.percentile(v, 97.5):.3f}]"
    P(f" k={k}: n aidev {np.mean(vals['n_a']):.0f} ghhuman {np.mean(vals['n_h']):.0f} | aidev {f(vals['aidev'])} ghhuman {f(vals['ghhuman'])} 差 {f(vals['diff'])}")

P("\n== (4) ロジスティック回帰 H ~ human(ghhuman=1) + closed(重みなし、n=%d、repo %d)" % (len(D), D.repo.nunique()))
D["human"] = (D.grp == "ghhuman").astype(int); D["closed"] = (D.st == "closed").astype(int)
r = smf.logit("H ~ human + closed", D).fit(disp=0)
ci = r.conf_int().loc["human"]
P(f" (a) 通常: OR(human) {np.exp(r.params['human']):.2f} (95%CI {np.exp(ci[0]):.2f}-{np.exp(ci[1]):.2f}) p={r.pvalues['human']:.3f}"
  f"  OR(closed) {np.exp(r.params['closed']):.2f} p={r.pvalues['closed']:.3f}")
rc = smf.logit("H ~ human + closed", D).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(D.repo)[0]})
ci = rc.conf_int().loc["human"]
P(f" (b) repo クラスタ頑健 SE: OR(human) {np.exp(rc.params['human']):.2f} (95%CI {np.exp(ci[0]):.2f}-{np.exp(ci[1]):.2f}) p={rc.pvalues['human']:.3f}")
ge = smf.gee("H ~ human + closed", "repo", D, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
ci = ge.conf_int().loc["human"]
P(f" (c) GEE 交換可能: OR(human) {np.exp(ge.params['human']):.2f} (95%CI {np.exp(ci[0]):.2f}-{np.exp(ci[1]):.2f}) p={ge.pvalues['human']:.3f}"
  f"  repo 内相関 {ge.cov_struct.dep_params:.3f}")
mm = BinomialBayesMixedGLM.from_formula("H ~ human + closed", {"repo": "0 + C(repo)"}, D).fit_vb()
i = list(mm.model.exog_names).index("human"); b, sd = mm.fe_mean[i], mm.fe_sd[i]
P(f" (d) repo 変量効果(VB): OR(human) {np.exp(b):.2f} (±1.96SD {np.exp(b - 1.96 * sd):.2f}-{np.exp(b + 1.96 * sd):.2f})"
  f"  repo 効果 SD(事後平均) {np.exp(mm.vcp_mean[0]):.3f}")
ri = smf.logit("H ~ human * closed", D).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(D.repo)[0]})
for t in ["human", "human:closed"]:
    ci = ri.conf_int().loc[t]
    P(f" (e) 交互作用モデル(repo クラスタ頑健 SE) OR({t}) {np.exp(ri.params[t]):.2f} (95%CI {np.exp(ci[0]):.2f}-{np.exp(ci[1]):.2f}) p={ri.pvalues[t]:.3f}")
P(" ※ (e) の OR(human) は not_closed 層での人間/エージェント比")
# 結末層ごとの生の比率
P("\n== 参考: 群×結末層の生の H 率")
for (g, s), d in D.groupby(["grp", "st"]):
    P(f" {g} {s}: {d.H.sum()}/{len(d)} = {d.H.mean():.3f}")
hd = D[(D.grp == "ghhuman") & (D.repo == "home-assistant/core")]
P(f" ghhuman の home-assistant/core 有効 {len(hd)} 件: H {hd.H.sum()}(層 {hd.st.value_counts().to_dict()})")
P(" ※ (0) は有効件数で層のサンプル数を数えるため、compare.txt(全件で数える)と小数第3位がずれる")
open(f"{ROOT}/work/baseline/repo_sensitivity.txt", "w").write("\n".join(out) + "\n"); print("\n".join(out))
