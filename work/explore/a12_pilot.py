"""分析1・2(pilot = GitHub 39 repo):CR を出したレビュアーの属性と、CR 後の結末。
対象: work/baseline/within/blocks_agent.jsonl(pilot の CR 5,918 件、agent_level 付き)
属性(すべて当該 CR の日時より前、その repo 内):
  merges_before = そのレビュアーが merge した PR 数(merged_by.jsonl × prs_full.mergedAt)→ >0 を「merge 権限あり」の代理
  authored_before = 作成 PR 数 / reviews_before = レビュー数(prs_full の reviews ノード、取得上限で欠ける可能性)
  codeowner = その月の CODEOWNERS スナップショットに @login がある
結末: outcome(merged/closed/open)、CR 後のコミット有無(committedDate > CR 日時)、CR 後の同レビュアー APPROVED、CR→merge 時間
uv run python work/explore/a12_pilot.py"""
import json, os, collections, csv, re, random, bisect
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
E = os.path.join(ROOT, "work/explore"); P = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/pilot_raw_full"))
blocks = [json.loads(l) for l in open(os.path.join(ROOT, "work/baseline/within/blocks_agent.jsonl"))]
repos = sorted({b["repo"] for b in blocks})
info = {}
for repo in repos:
    d = os.path.join(P, repo.replace("/", "__"))
    prs = {}
    for l in open(os.path.join(d, "prs_full.jsonl")):
        try: j = json.loads(l)
        except Exception: continue
        prs[j["number"]] = j
    mb = {}
    for l in open(os.path.join(d, "merged_by.jsonl")):
        try: j = json.loads(l)
        except Exception: continue
        mb[j["number"]] = j.get("merged_by")
    merges = collections.defaultdict(list); authored = collections.defaultdict(list); reviews = collections.defaultdict(list)
    for n, j in prs.items():
        a = (j.get("author") or {}).get("login")
        if a: authored[a.lower()].append(j["createdAt"])
        if j.get("mergedAt") and mb.get(n): merges[mb[n].lower()].append(j["mergedAt"])
        for r in (j.get("reviews") or {}).get("nodes", []):
            ra = (r.get("author") or {}).get("login")
            if ra and r.get("submittedAt"): reviews[ra.lower()].append(r["submittedAt"])
    for dct in (merges, authored, reviews):
        for k in dct: dct[k].sort()
    co = {}
    sd = os.path.join(d, "codeowners/snapshots")
    if os.path.isdir(sd):
        for fn in os.listdir(sd):
            co[fn[:7]] = set(m.lower() for m in re.findall(r"@([A-Za-z0-9_.-]+)", open(os.path.join(sd, fn), errors="replace").read()))
    info[repo] = dict(prs=prs, merges=merges, authored=authored, reviews=reviews, co=co)

def cnt(lst, t): return bisect.bisect_left(lst, t)
rows = []
for b in blocks:
    I = info[b["repo"]]; who = b["reviewer"].lower(); t = b["submittedAt"]; j = I["prs"].get(b["number"], {})
    commits = [c["commit"]["committedDate"] for c in (j.get("commits") or {}).get("nodes", [])]
    later_rv = [r for r in (j.get("reviews") or {}).get("nodes", []) if (r.get("submittedAt") or "") > t and ((r.get("author") or {}).get("login") or "").lower() == who]
    m = j.get("mergedAt")
    hrs = None
    if m:
        from datetime import datetime
        f = lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
        hrs = (f(m) - f(t)).total_seconds() / 3600
    co = I["co"].get(t[:7])
    rows.append(dict(rid=b["rid"], repo=b["repo"], agent_level=b.get("agent_level"), outcome=b["outcome"], reviewer=b["reviewer"],
                     merges_before=cnt(I["merges"].get(who, []), t), authored_before=cnt(I["authored"].get(who, []), t),
                     reviews_before=cnt(I["reviews"].get(who, []), t), codeowner=(None if co is None else who in co),
                     commit_after=any(c > t for c in commits), approve_after=any(r["state"] == "APPROVED" for r in later_rv),
                     hrs_to_merge=hrs, body_len=len((b.get("body") or "").strip()) + sum(len(str(c.get("body", ""))) for c in (b.get("comments") or []))))
with open(os.path.join(E, "a12_pilot_blocks.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
R = {r["rid"]: r for r in rows}

def ci_prop(x, B=4000, seed=0):
    r = random.Random(seed); n = len(x)
    if n == 0: return (float("nan"),) * 2
    bs = sorted(np.mean([r.choice(x) for _ in range(n)]) for _ in range(B))
    return bs[int(B * .025)], bs[int(B * .975)]
def diff_ci(a, b, B=4000, seed=1):
    r = random.Random(seed)
    bs = sorted(np.mean([r.choice(a) for _ in a]) - np.mean([r.choice(b) for _ in b]) for _ in range(B))
    return np.mean(a) - np.mean(b), bs[int(B * .025)], bs[int(B * .975)]

print("== 母集団: pilot CR", len(rows))
for lv in ("none", "weak", "strong", None):
    ss = [r for r in rows if lv is None or r["agent_level"] == lv]
    if not ss: continue
    mg = [r["merges_before"] > 0 for r in ss]
    print(f" agent_level={lv or '全体'} n={len(ss)} merge権限あり {np.mean(mg):.3f} codeowner {np.mean([bool(r['codeowner']) for r in ss if r['codeowner'] is not None]):.3f}"
          f" | CR後コミット {np.mean([r['commit_after'] for r in ss]):.3f} 同レビュアー承認 {np.mean([r['approve_after'] for r in ss]):.3f}"
          f" merged {np.mean([r['outcome']=='merged' for r in ss]):.3f} closed {np.mean([r['outcome']=='closed' for r in ss]):.3f}")
print(" 結末 × merge権限(全体)")
for g in (True, False):
    ss = [r for r in rows if (r["merges_before"] > 0) == g]
    print(f"  merge権限{'あり' if g else 'なし'} n={len(ss)} merged {np.mean([r['outcome']=='merged' for r in ss]):.3f} closed {np.mean([r['outcome']=='closed' for r in ss]):.3f} CR後コミット {np.mean([r['commit_after'] for r in ss]):.3f}")

def labeled(path, idkey="rid", catkey="majority", grpkey=None):
    out = []
    for r in csv.DictReader(open(path)):
        out.append(r)
    return out
print("\n== ラベル付きサンプル × 属性・結末")
smp_h = {s["sid"]: s for s in json.load(open(os.path.join(ROOT, "outputs/ghhuman/sample100.json")))}
smp_w = {s["sid"]: s for s in json.load(open(os.path.join(ROOT, "work/baseline/within/sample.json")))}
lab = []
for r in csv.DictReader(open(os.path.join(ROOT, "outputs/ghhuman/irr/irr_merged.csv"))):
    lab.append(dict(src="ghhuman", sid=r["sid"], grp="HUMAN100", cat=r["majority"], rid=smp_h[r["sid"]]["rid"]))
for r in csv.DictReader(open(os.path.join(ROOT, "work/baseline/within/irr/irr_merged.csv"))):
    s = smp_w[r["sid"]]
    if s["src"] != "pilot": continue
    lab.append(dict(src="within", sid=r["sid"], grp=s["grp"], cat=r["majority"], rid=s["rid"]))
out = []
for L in lab:
    if L["cat"] in ("BOT", "UNK", "NOAGREE") or L["rid"] not in R: continue
    x = dict(L); x.update(R[L["rid"]]); x["H"] = L["cat"].startswith("H"); out.append(x)
with open(os.path.join(E, "a12_pilot_labeled.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print(" 結合できたラベル", collections.Counter(x["grp"] for x in out), "(rid 不一致は除外)")
for name, ss in (("ghhuman100", [x for x in out if x["src"] == "ghhuman"]), ("within AG+HU+HO(pilot)", [x for x in out if x["src"] == "within"]),
                 ("within AG", [x for x in out if x["grp"] == "AG"]), ("within HU+HO", [x for x in out if x["grp"] in ("HU", "HO")])):
    a = [x["H"] for x in ss if x["merges_before"] > 0]; b = [x["H"] for x in ss if x["merges_before"] == 0]
    print(f" [{name}] n={len(ss)} merge権限あり H {sum(a)}/{len(a)} なし H {sum(b)}/{len(b)}", end="")
    if a and b: print(" 差 %+.3f 95%%CI %.3f..%.3f" % diff_ci(a, b))
    else: print()
    c = [x["H"] for x in ss if x["codeowner"] is True]; d = [x["H"] for x in ss if x["codeowner"] is False]
    print(f"   codeowner H {sum(c)}/{len(c)} 非 H {sum(d)}/{len(d)}")
    for g in (True, False):
        t = [x for x in ss if x["H"] == g]
        if not t: continue
        hm = [x["hrs_to_merge"] for x in t if x["hrs_to_merge"] is not None]
        print(f"   {'H' if g else 'C'}系 n={len(t)} merged {np.mean([x['outcome']=='merged' for x in t]):.2f} closed {np.mean([x['outcome']=='closed' for x in t]):.2f}"
              f" CR後コミット {np.mean([x['commit_after'] for x in t]):.2f} 同レビュアー承認 {np.mean([x['approve_after'] for x in t]):.2f}"
              f" CR→merge 中央値 {np.median(hm) if hm else float('nan'):.1f}h (n={len(hm)})")
    a = [x["outcome"] == "closed" for x in ss if x["H"]]; b = [x["outcome"] == "closed" for x in ss if not x["H"]]
    if a and b: print("   closed 率 H−C %+.3f 95%%CI %.3f..%.3f" % diff_ci(a, b))
    a = [x["commit_after"] for x in ss if x["H"]]; b = [x["commit_after"] for x in ss if not x["H"]]
    if a and b: print("   CR後コミット率 H−C %+.3f 95%%CI %.3f..%.3f" % diff_ci(a, b))
