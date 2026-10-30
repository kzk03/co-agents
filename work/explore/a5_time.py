"""分析5: AIDev 期間内の時系列。CR 率(人間 CR が1件以上ある PR / PR)と、CR 本文の H系的語彙率(辞書 HDICT)。
辞書の妥当性を、ラベル付き標本(AIDev100 / ghhuman100 / within158 / Gerrit100 の v0 多数決)で先に確認する。
同一 repo 内の変化 = repo ごとに自分の PR 作成日の中央値で前半/後半に分け、後半−前半の差を repo 単位 bootstrap。
uv run python work/explore/a5_time.py"""
import os, re, json, csv, random, collections, ast
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
HDICT = r"\b(why|instead|not needed|unnecessary|don't want|do not want|we decided|roadmap|scope|design|approach|breaking|backwards?[- ]compat\w*|policy|users?|customers?|discuss\w*|prefer\w*|not the right|should not|shouldn't|revert|security|licen[sc]e|permission|intent\w*|direction|maintainers?|consensus|product|out of scope|not sure we|do we (?:want|need))\b"
CDICT = r"\b(test|tests|typo|lint|format\w*|fail\w*|error|bug|null|exception|rename|import|unused|compile|build|ci|docstring|comment)\b"
RH, RC = re.compile(HDICT, re.I), re.compile(CDICT, re.I)
out = []
def p(s): out.append(s); print(s)
def bdiff(a, b, B=3000, seed=0):
    r = random.Random(seed)
    bs = sorted(np.mean([r.choice(a) for _ in a]) - np.mean([r.choice(b) for _ in b]) for _ in range(B))
    return np.mean(a) - np.mean(b), bs[int(B * .025)], bs[int(B * .975)]

# ---- 辞書の妥当性
def txt_of(s):
    t = str(s.get("body") or "")
    c = s.get("comments") if "comments" in s else s.get("inline")
    if isinstance(c, str):
        try: c = ast.literal_eval(c)
        except Exception: c = []
    for x in c or []:
        if isinstance(x, dict): t += "\n" + str(x.get("body") or x.get("message") or "")
    return t
val = []
for smp, lab, key in [("outputs/aidev/sample100.json", "outputs/aidev/irr/irr_merged.csv", "aidev"),
                      ("outputs/ghhuman/sample100.json", "outputs/ghhuman/irr/irr_merged.csv", "ghhuman"),
                      ("work/baseline/within/sample.json", "work/baseline/within/irr/irr_merged.csv", "within"),
                      ("outputs/gerrit/gerrit_pilot_sample100.json", "outputs/gerrit/irr/irr_merged.csv", "gerrit")]:
    S = {s["sid"]: s for s in json.load(open(os.path.join(ROOT, smp)))}
    for r in csv.DictReader(open(os.path.join(ROOT, lab))):
        if r["majority"] in ("BOT", "UNK", "NOAGREE") or r["sid"] not in S: continue
        t = txt_of(S[r["sid"]])
        val.append(dict(set=key, H=r["majority"].startswith("H"), dh=bool(RH.search(t)), dc=bool(RC.search(t))))
p("== 辞書の妥当性(v0 多数決 H と、HDICT ヒット)")
for key in ("aidev", "ghhuman", "within", "gerrit", "all"):
    v = [x for x in val if key == "all" or x["set"] == key]
    tp = sum(x["H"] and x["dh"] for x in v); fp = sum(not x["H"] and x["dh"] for x in v); fn = sum(x["H"] and not x["dh"] for x in v)
    h1 = np.mean([x["dh"] for x in v if x["H"]]); h0 = np.mean([x["dh"] for x in v if not x["H"]])
    p(f" {key:8s} n={len(v)} H中のヒット率 {h1:.2f} C中のヒット率 {h0:.2f} 精度 {tp/max(tp+fp,1):.2f} 再現 {tp/max(tp+fn,1):.2f}")

# ---- AIDev 全体
pr = pd.read_parquet(os.path.join(ROOT, "data/aidev/pull_request.parquet"))
rv = pd.read_parquet(os.path.join(ROOT, "data/aidev/pr_reviews.parquet"))
rc = pd.read_parquet(os.path.join(ROOT, "data/aidev/pr_review_comments.parquet"))
cr = rv[(rv.state == "CHANGES_REQUESTED") & (rv.user_type == "User")].copy()
ib = rc.groupby("pull_request_review_id").body.apply(lambda s: "\n".join(map(str, s)))
cr["text"] = cr.body.fillna("") + "\n" + cr.id.map(ib).fillna("")
cr["dh"] = cr.text.map(lambda t: bool(RH.search(t))); cr["dc"] = cr.text.map(lambda t: bool(RC.search(t)))
pr["month"] = pr.created_at.str[:7]; pr["cr"] = pr.id.isin(cr.pr_id)
cr = cr.merge(pr[["id", "repo_url", "agent", "created_at"]].rename(columns={"id": "pr_id"}), on="pr_id")
cr["month"] = cr.submitted_at.str[:7]
p("\n== 月別(PR 作成月): PR数 / CR率 / CR数 / H語彙率 / C語彙率(全体, Copilot のみ)")
for m, d in pr.groupby("month"):
    c = cr[cr.month == m]; dc = d[d.agent == "Copilot"]; cc = c[c.agent == "Copilot"]
    p(f" {m} PR {len(d):6d} CR率 {d.cr.mean():.4f} CR {len(c):4d} H語彙 {c.dh.mean() if len(c) else float('nan'):.2f} C語彙 {c.dc.mean() if len(c) else float('nan'):.2f}"
      f" | Copilot PR {len(dc):5d} CR率 {dc.cr.mean() if len(dc) else float('nan'):.4f} H語彙 {cc.dh.mean() if len(cc) else float('nan'):.2f}")
p(f" 全体 H語彙率 {cr.dh.mean():.3f}(n={len(cr)})")

# ---- 同一 repo 内 前半/後半
p("\n== 同一 repo 内:前半→後半(repo ごとに PR 作成日の中央値で分割)")
prc = pr[(pr.state == "closed") & (pr.created_at < "2025-10-01")]  # 打ち切り対策: 閉じた PR かつ 9月までに作成
for name, P0 in (("全エージェント", pr), ("Copilot のみ", pr[pr.agent == "Copilot"]), ("Codex のみ", pr[pr.agent == "OpenAI_Codex"]),
                 ("頑健性: 全エージェント closed&<2025-10", prc), ("頑健性: Copilot closed&<2025-10", prc[prc.agent == "Copilot"])):
    a, b, ha, hb = [], [], [], []
    for repo, d in P0.groupby("repo_url"):
        if len(d) < 20: continue
        med = sorted(d.created_at)[len(d) // 2]; e, l = d[d.created_at <= med], d[d.created_at > med]
        if len(e) < 5 or len(l) < 5: continue
        a.append(e.cr.mean()); b.append(l.cr.mean())
        c = cr[cr.pr_id.isin(d.id)]
        ce, cl = c[c.pr_id.isin(e.id)], c[c.pr_id.isin(l.id)]
        if len(ce) >= 3 and len(cl) >= 3: ha.append(ce.dh.mean()); hb.append(cl.dh.mean())
    dd0 = np.array(b) - np.array(a); r0 = random.Random(0)
    bs0 = sorted(np.mean([r0.choice(list(dd0)) for _ in dd0]) for _ in range(3000))
    p(f" [{name}] repo {len(a)}(PR>=20) CR率 前半 {np.mean(a):.4f} 後半 {np.mean(b):.4f} 対応差 {dd0.mean():+.4f} 95%CI {bs0[75]:+.4f}..{bs0[2925]:+.4f}"
      f" | 減少 repo 割合 {np.mean(dd0<0):.2f} 増加 {np.mean(dd0>0):.2f} 不変 {np.mean(dd0==0):.2f}")
    if ha:
        dd = np.array(hb) - np.array(ha); r = random.Random(0)
        bs = sorted(np.mean([r.choice(list(dd)) for _ in dd]) for _ in range(3000))
        p(f"   H語彙率(CR>=3 が両半にある repo {len(ha)}) 前半 {np.mean(ha):.2f} 後半 {np.mean(hb):.2f} 対応差 {dd.mean():+.3f} 95%CI {bs[75]:+.3f}..{bs[2925]:+.3f}")
open(os.path.join(ROOT, "work/explore/a5_time.out"), "w").write("\n".join(out) + "\n")
