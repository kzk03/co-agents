"""分析1(Gerrit): -1/-2 を出すレビュアーの属性と v0 ラベル・結末。
core = その project のデータ中で Code-Review +2/-2 か Workflow +1 を一度でも付けた account(期間全体、事後情報を含む近似)。
経験 = 当該投票日より前に、その project で owner になった change 数 / Code-Review 投票(非0)数。
uv run python work/explore/a1_gerrit.py"""
import json, glob, os, collections, csv, random
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
E = os.path.join(ROOT, "work/explore")
allv = json.load(open(os.path.join(ROOT, "outputs/gerrit/gerrit_neg_votes_all.json")))
core = collections.defaultdict(set)          # project -> accounts
owned = collections.defaultdict(list)        # (project, acc) -> created dates
votes = collections.defaultdict(list)        # (project, acc) -> CR vote dates
status = {}
for f in sorted(glob.glob(os.path.join(ROOT, "data/raw_json/*.json"))):
    for ch in json.load(open(f)):
        p = ch["project"]; status[(p, ch["_number"])] = ch["status"]
        owned[(p, ch["owner"]["_account_id"])].append(ch["created"][:19])
        lab = ch.get("labels") or {}
        for v in (lab.get("Code-Review") or {}).get("all", []):
            if v.get("value") in (2, -2): core[p].add(v["_account_id"])
            if v.get("value"): votes[(p, v["_account_id"])].append((v.get("date") or "")[:19])
        for v in (lab.get("Workflow") or {}).get("all", []):
            if v.get("value") == 1: core[p].add(v["_account_id"])
def before(lst, d): return sum(1 for x in lst if x and x < d)

def boot_diff(a, b, B=4000, seed=0):
    r = random.Random(seed); out = []
    for _ in range(B):
        x = [r.choice(a) for _ in a]; y = [r.choice(b) for _ in b]
        out.append(np.mean(x) - np.mean(y))
    return np.percentile(out, [2.5, 97.5])

print("== 母集団: -1/-2 投票", len(allv))
rows = []
for v in allv:
    p = v["project"]; acc = v["reviewer"]; d = v["date"][:19]
    rows.append(dict(vote=v["vote"], core=acc in core[p], self=v["is_self"], st=v["status"],
                     own=before(owned[(p, acc)], d)))
for vote in (-1, -2):
    rs = [r for r in rows if r["vote"] == vote and not r["self"]]
    c = [r for r in rs if r["core"]]
    print(f" vote {vote}: n={len(rs)} core 比率 {len(c)/len(rs):.3f}")
    for g, name in ((True, "core"), (False, "非core")):
        ss = [r for r in rs if r["core"] == g]
        if not ss: continue
        ab = [r["st"] == "ABANDONED" for r in ss]; mg = [r["st"] == "MERGED" for r in ss]
        print(f"   {name}: n={len(ss)} 最終 MERGED {np.mean(mg):.3f} ABANDONED {np.mean(ab):.3f}")
    a = [r["st"] == "ABANDONED" for r in rs if r["core"]]; b = [r["st"] == "ABANDONED" for r in rs if not r["core"]]
    if a and b:
        print(f"   ABANDONED 差 core−非core {np.mean(a)-np.mean(b):+.3f} 95%CI {boot_diff(a,b,1000)}")

print("\n== サンプル100 × v0 多数決ラベル")
out = []
for setname in ("gerrit", "gerrit_blind"):
    smp = json.load(open(os.path.join(ROOT, f"outputs/{setname}/gerrit_pilot_sample100.json")))
    lab = {r["sid"]: r for r in csv.DictReader(open(os.path.join(ROOT, f"outputs/{setname}/irr/irr_merged.csv")))}
    recs = []
    for s in smp:
        p = s["project"]; acc = int(s["reviewer"]); d = s["date"][:19]; m = lab.get(s["sid"], {"majority": "UNK"})["majority"]
        if m in ("BOT", "UNK", "NOAGREE"): continue
        r = dict(sid=s["sid"], set=setname, vote=int(s["vote"]), H=m.startswith("H"), cat=m, core=acc in core[p],
                 own=before(owned[(p, acc)], d), status=s["status"])
        recs.append(r); out.append(r)
    c = [r["H"] for r in recs if r["core"]]; n = [r["H"] for r in recs if not r["core"]]
    print(f" [{setname}] 有効 n={len(recs)} core {len(c)} 件 H {sum(c)}/{len(c)}={np.mean(c):.3f} | 非core {len(n)} 件 H {sum(n)}/{len(n)}={np.mean(n) if n else float('nan'):.3f} | 差 {np.mean(c)-np.mean(n):+.3f} 95%CI {boot_diff(c,n)}")
    m1 = [r for r in recs if r["vote"] == -1]
    c = [r["H"] for r in m1 if r["core"]]; n = [r["H"] for r in m1 if not r["core"]]
    print(f"   -1 のみ: core H {sum(c)}/{len(c)}  非core H {sum(n)}/{len(n)}  差 {np.mean(c)-np.mean(n):+.3f} 95%CI {boot_diff(c,n)}")
    # 経験(過去 owner 件数)の中央値で分割
    med = np.median([r["own"] for r in recs])
    hi = [r["H"] for r in recs if r["own"] > med]; lo = [r["H"] for r in recs if r["own"] <= med]
    print(f"   過去 owner 件数 > 中央値{med:.0f}: H {sum(hi)}/{len(hi)}  ≤: H {sum(lo)}/{len(lo)}")
    # 結末
    for g in (True, False):
        ss = [r for r in recs if r["H"] == g]
        print(f"   {'H' if g else 'C'}系: n={len(ss)} 最終 ABANDONED {sum(r['status']=='ABANDONED' for r in ss)} MERGED {sum(r['status']=='MERGED' for r in ss)}")
with open(os.path.join(E, "a1_gerrit_sample.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
