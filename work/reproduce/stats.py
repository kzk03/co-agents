"""再現実験の集計。uv run python work/reproduce/stats.py  → results/stats_v0.txt, results/stats_v1.txt, results/judgments_long.csv
v0: protocol §4(判定 v0 プロンプト、A/B、AIDev 18件)
v1: 変更履歴 v1(盲検判定、A/B/C、top3、AIDev 拡張 + ghhuman)
"""
import glob, json, math, os, re, sys
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
W = os.path.join(ROOT, "work/reproduce")
LAB = ["yes", "partial", "no"]


def parse_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    return json.loads(m.group(0)) if m else None


def kappa(a, b, labels):
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def fisher_two_sided(a, b, c, d):
    """2x2 [[a,b],[c,d]] の Fisher 正確検定(両側)。"""
    r1, r2, c1, n = a + b, c + d, a + c, a + b + c + d
    def p(x):
        return math.comb(r1, x) * math.comb(r2, c1 - x) / math.comb(n, c1)
    p0 = p(a); lo, hi = max(0, c1 - r2), min(r1, c1)
    return min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= p0 * (1 + 1e-9)))


def meta():
    rows = []
    for d, src in (("data", "aidev"), ("data_gh", "ghhuman")):
        for f in glob.glob(os.path.join(W, d, "[GH][0-9]*.json")):
            r = json.load(open(f))
            cx = os.path.join(W, "ctxc" if src == "aidev" else "ctxc_gh", os.path.basename(f))
            c = json.load(open(cx)) if os.path.exists(cx) else {}
            rows.append(dict(sid=r["sid"], src=src, grp=r["grp"], cat=r["cat"], inf=r["inf"], repo=r["repo"],
                             has_issue=bool(c.get("issue_text")), n_disc=c.get("n_disc"), same_rev=c.get("n_disc_same_reviewer")))
    m = pd.DataFrame(rows).set_index("sid")
    v0 = {x["sid"] for x in json.load(open(os.path.join(W, "data/_fetch_log.json"))) if x["status"] == "OK"}
    m["v0"] = m.index.isin(v0)
    return m


def load_judgments():
    """long 形式: sid, judge, version, cond, label, item"""
    L = []
    # v0 sonnet
    for f in glob.glob(os.path.join(W, "results/G*_judge.json")):
        j = json.load(open(f)); p = parse_json(j.get("text"))
        if j.get("is_error") or not p:
            continue
        for c in "AB":
            L.append(dict(sid=j["sid"], judge="sonnet", version="v0", cond=c, label=p[c], item=None))
    # v1 sonnet(盲検、並べ替えを戻す)
    for d in ("results", "results_gh"):
        for f in glob.glob(os.path.join(W, d, "*_judge_v1.json")):
            j = json.load(open(f)); p = parse_json(j.get("text"))
            if j.get("is_error") or not p:
                continue
            for i, c in enumerate(j["order"]):
                L.append(dict(sid=j["sid"], judge="sonnet", version="v1", cond=c, label=p[f"R{i+1}"], item=int(p.get(f"R{i+1}_item") or 0)))
    # Opus(私)
    me0 = pd.read_csv(os.path.join(W, "judge_me.csv"))
    for _, r in me0.iterrows():
        for c in "AB":
            L.append(dict(sid=r.sid, judge="opus", version="v0", cond=c, label=r[c], item=int(r[f"{c}_item"])))
    f1 = os.path.join(W, "judge_me_v1.csv")
    if os.path.exists(f1):
        me1 = pd.read_csv(f1)
        for _, r in me1.iterrows():
            for c in "ABC":
                if isinstance(r.get(c), str):
                    L.append(dict(sid=r.sid, judge="opus", version="v1", cond=c, label=r[c], item=int(r[f"{c}_item"])))
    fcr = os.path.join(W, "judge_me_cr.csv")
    if os.path.exists(fcr):
        for _, r in pd.read_csv(fcr).iterrows():
            L.append(dict(sid=r.sid, judge="opus", version="v1", cond="Cr", label=r.Cr, item=int(r.Cr_item)))
    df = pd.DataFrame(L)
    df["label"] = df.label.str.strip().str.lower()
    return df


def recall_table(d, m, out, title, top3=False):
    d = d.join(m[["grp"]], on="sid")
    out.append(f"\n## {title}")
    out.append("cond grp  n  yes  yes%  [95%CI]        yes+partial%" + ("  top3yes%" if top3 else ""))
    for c in sorted(d.cond.unique()):
        cell = {}
        for g in ("H", "C"):
            x = d[(d.cond == c) & (d.grp == g)]; n = len(x)
            if n == 0:
                continue
            k = (x.label == "yes").sum(); kp = x.label.isin(["yes", "partial"]).sum(); lo, hi = wilson(k, n)
            s = f"{c:>4} {g:>3} {n:>2} {k:>4}  {k/n:5.1%} [{lo:.2f}-{hi:.2f}]  {kp/n:6.1%}"
            if top3:
                k3 = ((x.label == "yes") & (x["item"].between(1, 3))).sum(); s += f"   {k3/n:6.1%} ({k3})"
                cell[g + "3"] = (k3, n)
            cell[g] = (k, n); cell[g + "p"] = (kp, n)
            out.append(s)
        if "H" in cell and "C" in cell:
            (kh, nh), (kc, nc) = cell["H"], cell["C"]
            out.append(f"     Fisher(yes, H vs C) p={fisher_two_sided(kh, nh - kh, kc, nc - kc):.3f};  "
                       f"yes+partial p={fisher_two_sided(cell['Hp'][0], nh - cell['Hp'][0], cell['Cp'][0], nc - cell['Cp'][0]):.3f}")


def agreement(d, out, title, conds):
    out.append(f"\n## {title}")
    for cs in [[c] for c in conds] + ([conds] if len(conds) > 1 else []):
        x = d[d.cond.isin(cs)].pivot_table(index=["sid", "cond"], columns="judge", values="label", aggfunc="first").dropna()
        if len(x) == 0 or not {"opus", "sonnet"} <= set(x.columns):
            continue
        a, b = list(x.opus), list(x.sonnet)
        a2 = ["yes" if v == "yes" else "non" for v in a]; b2 = ["yes" if v == "yes" else "non" for v in b]
        out.append(f"cond={'+'.join(cs)} n={len(x)}  一致率(3値)={sum(i == j for i, j in zip(a, b))/len(a):.3f}  κ3={kappa(a, b, LAB):.3f}  "
                   f"一致率(yes/非yes)={sum(i == j for i, j in zip(a2, b2))/len(a2):.3f}  κ2={kappa(a2, b2, ['yes', 'non']):.3f}")
        if cs == conds:
            out.append("混同行列(行=opus, 列=sonnet)\n" + pd.crosstab(x.opus, x.sonnet).reindex(index=LAB, columns=LAB, fill_value=0).to_string())


def crosstab_inf(d, m, out, title):
    d = d.join(m[["inf", "grp"]], on="sid")
    out.append(f"\n## {title}")
    for c in sorted(d.cond.unique()):
        x = d[d.cond == c]
        out.append(f"cond={c}(行=主観 majority_inf, 列=実測)\n" +
                   pd.crosstab(x.inf, x.label).reindex(columns=LAB, fill_value=0).to_string())


def main():
    m = meta(); J = load_judgments()
    J.to_csv(os.path.join(W, "results/judgments_long.csv"), index=False)
    # ---------------- v0 ----------------
    out = ["# v0 集計(protocol §4。AIDev 18件)",
           "注: 予算超過のため sonnet 列は §4 の v0 判定プロンプトではなく v1 盲検判定の A/B(変更履歴 2026-10-22)。opus 列は judge_me.csv。",
           f"群: {m[m.v0].grp.value_counts().to_dict()}"]
    sv0 = J[(J.version == "v0") & (J.judge == "sonnet")]
    if len(sv0) == 0:
        sv0 = J[(J.version == "v1") & (J.judge == "sonnet") & J.cond.isin(["A", "B"])].assign(version="v0")
    v0 = pd.concat([J[(J.version == "v0") & (J.judge == "opus")], sv0])
    v0 = v0[v0.sid.isin(m[m.v0].index)]
    for jd in ("opus", "sonnet"):
        recall_table(v0[v0.judge == jd], m, out, f"再現率(判定者={jd})")
    agreement(v0, out, "判定者間一致 opus vs sonnet(v0)", ["A", "B"])
    for jd in ("opus", "sonnet"):
        crosstab_inf(v0[v0.judge == jd], m, out, f"主観 inferable × 実測(判定者={jd})")
    open(os.path.join(W, "results/stats_v0.txt"), "w").write("\n".join(out) + "\n"); print("\n".join(out))
    # ---------------- v1 ----------------
    v1 = J[J.version == "v1"].copy()
    if len(v1) == 0:
        return
    # opus v1 の A/B は v0 判定(judge_me.csv)を引き継ぐ(v0 の18件は v1 で A/B を再判定していない)
    keep = v1[~((v1.judge == "opus") & v1.cond.isin(["A", "B"]) & v1.sid.isin(m[m.v0].index))]
    opus_v0 = J[(J.version == "v0") & (J.judge == "opus")]
    v1 = pd.concat([keep, opus_v0.assign(version="v1")])
    out = ["# v1 集計(盲検判定 v1、A/B/C、top3)"]
    for src in ("aidev", "ghhuman"):
        ms = m[m.src == src]
        if len(ms) == 0:
            continue
        out.append(f"\n# 標本={src} 群: {ms.grp.value_counts().to_dict()}")
        d = v1[v1.sid.isin(ms.index)]
        if len(d[d.judge == "sonnet"]) == 0:
            out.append("(判定なし: 未実施)")
            continue
        wide = d.pivot_table(index="sid", columns=["judge", "cond"], values="label", aggfunc="first")
        wide.columns = [f"{j}_{c}" for j, c in wide.columns]
        ms[["grp", "cat", "inf", "repo", "has_issue", "n_disc", "same_rev"]].join(wide).sort_values(["grp", "cat"]).to_csv(
            os.path.join(W, f"results/per_item_v1_{src}.csv"))
        for jd in ("sonnet", "opus"):
            recall_table(d[d.judge == jd], m, out, f"[{src}] 再現率(判定者={jd})", top3=True)
        agreement(d, out, f"[{src}] 判定者間一致 opus vs sonnet", sorted(d.cond.unique()))
        crosstab_inf(d[d.judge == "sonnet"], m, out, f"[{src}] 主観 inferable × 実測(sonnet v1)")
        # 条件C の感度分析: 同じレビュアーの先行発言を含む件を除く
        x = d[(d.cond == "C")].join(ms[["same_rev"]], on="sid")
        x = x[x.same_rev.fillna(0) == 0]
        recall_table(x[x.judge == "sonnet"].drop(columns="same_rev"), m, out, f"[{src}] 感度: 条件C、同レビュアーの先行発言なしの件のみ(sonnet)", top3=True)
        # 条件間の変化(sonnet): B→C
        p = d[d.judge == "sonnet"].pivot_table(index="sid", columns="cond", values="label", aggfunc="first").join(ms[["grp"]])
        if {"B", "C"} <= set(p.columns):
            out.append(f"\n## [{src}] B→C の遷移(sonnet、行=B 列=C)")
            for g in ("H", "C"):
                q = p[p.grp == g]
                out.append(f"grp={g}\n" + pd.crosstab(q.B, q.C).to_string())
        out.append(f"\n## [{src}] 標本メタ: Issue あり {int(ms.has_issue.sum())}/{len(ms)}、先行議論あり {(ms.n_disc.fillna(0) > 0).sum()}/{len(ms)}、"
                   f"同レビュアー先行発言あり {(ms.same_rev.fillna(0) > 0).sum()}/{len(ms)}")
    # ---- PR 本文リーク(leak.py)を考慮した感度分析 ----
    lk = os.path.join(W, "results/leakage_v1.csv")
    if os.path.exists(lk):
        L_ = pd.read_csv(lk).set_index("sid")
        clean = L_[L_.dataset_body_eq_at_review == True].index
        out.append(f"\n# PR 本文リーク: レビュー後に編集された本文を入力した件 = {int((L_.dataset_body_eq_at_review == False).sum())}/{len(L_)}"
                   f"(H {int(((L_.dataset_body_eq_at_review == False) & (L_.grp == 'H')).sum())}, C {int(((L_.dataset_body_eq_at_review == False) & (L_.grp == 'C')).sum())})")
        d = v1[v1.sid.isin(clean) & v1.cond.isin(["A", "B", "C"])]
        for jd in ("sonnet", "opus"):
            recall_table(d[d.judge == jd], m, out, f"[aidev] 感度: 本文がレビュー時点と一致する件のみ(判定者={jd})", top3=True)
        # リーク件の H系: C と Cr(本文をレビュー時点に戻した C)の比較(opus のみ)
        leakH = L_[(L_.dataset_body_eq_at_review == False) & (L_.grp == "H")].index
        x = v1[(v1.judge == "opus") & v1.sid.isin(leakH) & v1.cond.isin(["C", "Cr"])]
        out.append("\n## リークのあった H系 8件: 条件C(リーク本文) vs Cr(レビュー時点本文)、判定者=opus")
        out.append(x.pivot_table(index="sid", columns="cond", values="label", aggfunc="first").to_string())
        out.append("yes 数: " + x.groupby("cond").label.apply(lambda s: f"{(s == 'yes').sum()}/{len(s)}").to_string().replace("\n", "; "))
        # H系をリーク補正: 本文一致件は C、リーク件は Cr(opus)
        hc = pd.concat([v1[(v1.judge == "opus") & (v1.cond == "C") & v1.sid.isin(clean)],
                        v1[(v1.judge == "opus") & (v1.cond == "Cr")].assign(cond="C")])
        recall_table(hc, m, out, "[aidev] リーク補正版 条件C(H系: 本文一致件は C、リーク件は Cr。C系: 本文一致件のみ。判定者=opus)")
    # 作者の違い(sonnet, 条件ごと、H/C 別)
    out.append("\n# 作者の違い(sonnet v1、yes 率)")
    d = v1[v1.judge == "sonnet"].join(m[["src", "grp"]], on="sid")
    out.append(d.groupby(["cond", "grp", "src"]).label.apply(lambda s: f"{(s == 'yes').mean():.1%} ({(s == 'yes').sum()}/{len(s)})").unstack("src").to_string())
    open(os.path.join(W, "results/stats_v1.txt"), "w").write("\n".join(out) + "\n"); print("\n".join(out))


if __name__ == "__main__":
    main()
