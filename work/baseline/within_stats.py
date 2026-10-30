"""同一 repo 内比較の集計。コーダー一致(κ)・多数決・群別 H 系比率・repo 内比較。
群: AG(pilot, エージェント trailer 付き PR) / HU(pilot 人間 PR、AG と repo×結末層でマッチ)
    AO(AIDev エージェント PR、共通5 repo) / HO(pilot 人間 PR、AO と repo(×結末層)でマッチ)
差の区間: repo クラスタ・ブートストラップ(対になる2群を repo ごとに一緒に復元抽出、2000 回、seed 0)
回帰: H ~ 人間群 + closed + repo 固定効果(条件付き)… repo 数が少ないので Mantel-Haenszel 共通 OR も出す
実行(humans_md/ で): uv run work/baseline/within_stats.py → work/baseline/within/stats.txt, irr/irr_merged.csv
"""
import collections, csv, json, os, random, sys
import numpy as np, pandas as pd
from statsmodels.stats.contingency_tables import StratifiedTable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, f"{ROOT}/scripts")
import irr  # noqa: E402
W = f"{ROOT}/work/baseline/within"
out = []; P = lambda *a: out.append(" ".join(str(x) for x in a))
s = irr.paths("within")
me = {r["sid"]: r for r in csv.DictReader(open(f"{W}/coding_opus_v0.csv"))}
so, ha = irr.load(s, "sonnet"), irr.load(s, "haiku")
sids = [k for k in me if k in so and k in ha]
grp = lambda c: "H" if c.startswith("H") else ("C" if c[0] in "CM" else c)
P("n", len(sids), "(opus", len(me), "sonnet", len(so), "haiku", len(ha), ")")
for nm, f in [("cat", lambda x: x["cat"]), ("group(C/H/他)", lambda x: grp(x["cat"])), ("inferable", lambda x: x["inferable"])]:
    A, B, C = ([f(d[k]) for k in sids] for d in (me, so, ha))
    P(nm, "一致率/κ opus-sonnet %.2f/%.2f" % irr.kappa(A, B), "opus-haiku %.2f/%.2f" % irr.kappa(A, C),
      "sonnet-haiku %.2f/%.2f" % irr.kappa(B, C), "fleiss %.2f" % irr.fleiss(list(zip(A, B, C))))
smp = {r["sid"]: r for r in json.load(open(f"{W}/sample.json"))}
rows = []
with open(f"{W}/irr/irr_merged.csv", "w") as fo:
    w = csv.writer(fo); w.writerow(["sid", "grp", "repo", "outcome", "me_cat", "sonnet_cat", "haiku_cat", "majority", "majority_inf"])
    for k in sids:
        t = collections.Counter([me[k]["cat"], so[k]["cat"], ha[k]["cat"]]).most_common(1)[0]
        mj = t[0] if t[1] >= 2 else "NOAGREE"
        ti = collections.Counter([me[k]["inferable"], so[k]["inferable"], ha[k]["inferable"]]).most_common(1)[0]
        mi = ti[0] if ti[1] >= 2 else "NOAGREE"
        r = smp[k]; w.writerow([k, r["grp"], r["repo"], r["outcome"], me[k]["cat"], so[k]["cat"], ha[k]["cat"], mj, mi])
        rows.append(dict(sid=k, grp=r["grp"], repo=r["repo"], closed=int(r["outcome"] == "closed"), maj=mj, inf=mi,
                         opus=me[k]["cat"], sonnet=so[k]["cat"], haiku=ha[k]["cat"]))
D = pd.DataFrame(rows)

P("\n== 群別の多数決カテゴリ件数")
cats = ["C1", "C2", "C3", "M", "H1", "H2", "H3", "H4", "H5", "BOT", "UNK", "NOAGREE"]
P("cat".ljust(8), " ".join(g.rjust(4) for g in ["AG", "HU", "AO", "HO"]))
for c in cats:
    P(c.ljust(8), " ".join(str(((D.grp == g) & (D.maj == c)).sum()).rjust(4) for g in ["AG", "HU", "AO", "HO"]))

P("\n== 群別 H 系比率(有効 = BOT/UNK/NOAGREE 除外、重みなし。マッチ済みなので repo 構成は対の群でほぼ同じ)")
for col, lab in [("maj", "多数決"), ("opus", "Opus 単独"), ("sonnet", "Sonnet 単独"), ("haiku", "Haiku 単独")]:
    line = []
    for g in ["AG", "HU", "AO", "HO"]:
        d = D[(D.grp == g) & ~D[col].isin(["BOT", "UNK", "NOAGREE"])]
        line.append(f"{g} {d[col].str.startswith('H').sum()}/{len(d)}={d[col].str.startswith('H').mean():.3f}")
    P(f" {lab}: " + "  ".join(line))
for g in ["AG", "HU", "AO", "HO"]:
    d = D[(D.grp == g) & ~D.maj.isin(["BOT", "UNK", "NOAGREE"])]
    P(f"  {g}: closed {d[d.closed == 1].maj.str.startswith('H').sum()}/{(d.closed == 1).sum()}  not_closed "
      f"{d[d.closed == 0].maj.str.startswith('H').sum()}/{(d.closed == 0).sum()}  inferable=no {(d.inf == 'no').sum()}/{len(d)}"
      f"  UNK/NOAGREE {(D[D.grp == g].maj.isin(['UNK', 'NOAGREE'])).sum()}/{(D.grp == g).sum()}")


def compare(ga, gh, col="maj", B=2000):
    d = D[D.grp.isin([ga, gh]) & ~D[col].isin(["BOT", "UNK", "NOAGREE"])].copy()
    d["H"] = d[col].str.startswith("H").astype(int); d["human"] = (d.grp == gh).astype(int)
    pt = d[d.human == 1].H.mean() - d[d.human == 0].H.mean()
    rng = random.Random(0); by = {r: x for r, x in d.groupby("repo")}; keys = list(by); diffs = []
    for _ in range(B):
        x = pd.concat([by[rng.choice(keys)] for _ in keys])
        if x.human.nunique() == 2:
            diffs.append(x[x.human == 1].H.mean() - x[x.human == 0].H.mean())
    # Mantel-Haenszel(層 = repo×結末層、両群がそろう層のみ)
    tabs = []
    for _, x in d.groupby(["repo", "closed"]):
        if x.human.nunique() == 2:
            t = np.array([[((x.human == 1) & (x.H == 1)).sum(), ((x.human == 1) & (x.H == 0)).sum()],
                          [((x.human == 0) & (x.H == 1)).sum(), ((x.human == 0) & (x.H == 0)).sum()]], float)
            tabs.append(t + (0.5 if (t == 0).any() else 0))
    st = StratifiedTable(tabs); ci = st.oddsratio_pooled_confint()
    return (f"{gh}-{ga} 差 {pt:.3f}(repo クラスタ bootstrap 95%CI {np.percentile(diffs, 2.5):.3f}-{np.percentile(diffs, 97.5):.3f})"
            f" | MH 共通 OR(人間/エージェント、層 {len(tabs)}、0セルは+0.5) {st.oddsratio_pooled:.2f} ({ci[0]:.2f}-{ci[1]:.2f})"
            f" 検定 p={st.test_null_odds().pvalue:.3f} | n {len(d)}")


P("\n== repo 内比較(人間群 − エージェント群の H 系比率)")
for ga, gh in [("AG", "HU"), ("AO", "HO")]:
    for col in ["maj", "opus", "sonnet", "haiku"]:
        P(f" [{col}] " + compare(ga, gh, col))
# 2つの比較を合算(エージェント=AG+AO、人間=HU+HO)
D2 = D.copy(); D2["grp"] = D2.grp.map({"AG": "A", "AO": "A", "HU": "Hm", "HO": "Hm"}); D_bak = D; D = D2
P(" [maj 合算 AG+AO vs HU+HO] " + compare("A", "Hm")); D = D_bak

P("\n== 参考: ghhuman(人間 PR、repo 上限あり)100件の多数決 H 系比率 0.288(層補正)、aidev 0.176 は compare.txt")
open(f"{W}/stats.txt", "w").write("\n".join(out) + "\n"); print("\n".join(out))
