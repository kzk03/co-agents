"""私(Opus)と sonnet の v1 分類の一致率。uv run python work/codebook/agree.py"""
import collections, csv, glob, json, os
W = os.path.dirname(os.path.abspath(__file__))
me = {r["sid"]: r for r in csv.DictReader(open(os.path.join(W, "coding_me_v1.csv")))}
so = {}
for f in glob.glob(os.path.join(W, "sonnet/*.jsonl")):
    for l in open(f):
        if l.strip().startswith("{"):
            j = json.loads(l); so[j["sid"]] = j
tg = {t["sid"]: t for t in json.load(open(os.path.join(W, "targets.json")))}
sids = [s for s in tg if s in me and s in so]
def grp(c):
    c = c.strip()
    if c in ("C1", "C2", "C3", "M"): return "C"
    if c.startswith("K"): return "K"
    if c.startswith("R"): return "R"
    if c.startswith("D"): return "D"
    return c
def kappa(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = collections.Counter(a), collections.Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / n / n
    return po, (po - pe) / (1 - pe) if pe < 1 else float("nan")
def hum(c):  # HUMANS.md 固有(D, K-priv, R-gov)か
    return "HU" if (c.startswith("D") or c in ("K-priv", "R-gov")) else "other"
print("n", len(sids), "missing sonnet", [s for s in tg if s not in so])
for label, f in [("cat(9値)", lambda c: c.strip()), ("group C/K/R/D/X", grp), ("HUMANS固有 vs 他", hum)]:
    a = [f(me[s]["v1"]) for s in sids]; b = [f(so[s]["cat"]) for s in sids]
    po, k = kappa(a, b); print(f"{label}: 一致 {po:.2f} κ {k:.2f}")
    for name in ("aidev", "ghhuman"):
        ss = [s for s in sids if tg[s]["set"] == name]
        po, k = kappa([f(me[s]["v1"]) for s in ss], [f(so[s]["cat"]) for s in ss]); print(f"   {name} n={len(ss)} 一致 {po:.2f} κ {k:.2f}")
dd = [(me[s]["doc_ex"], so[s]["doc"]) for s in sids]
po, k = kappa(*zip(*dd)); print(f"doc(could/no/-): 一致 {po:.2f} κ {k:.2f}")
dd2 = [(a, b) for a, b in dd if a != "-" and b != "-"]
po, k = kappa(*zip(*dd2)); print(f"doc 両者 K/R/D の件 n={len(dd2)}: 一致 {po:.2f} κ {k:.2f}")
print("\n分布 me:", collections.Counter(me[s]["v1"] for s in sids))
print("分布 sonnet:", collections.Counter(so[s]["cat"] for s in sids))
for name in ("aidev", "ghhuman"):
    ss = [s for s in sids if tg[s]["set"] == name]
    print(name, "me group", collections.Counter(grp(me[s]["v1"]) for s in ss), "| sonnet group", collections.Counter(grp(so[s]["cat"]) for s in ss))
print("\nクロス表 group(行=me, 列=sonnet)")
G = ["C", "K", "R", "D", "X", "UNK"]
ct = collections.Counter((grp(me[s]["v1"]), grp(so[s]["cat"])) for s in sids)
print("     " + " ".join(f"{g:>4}" for g in G))
for g in G: print(f"{g:>4} " + " ".join(f"{ct[(g, h)]:>4}" for h in G))
print("\nv0 多数決 × v1(me) group")
ct = collections.Counter((tg[s]["v0"], grp(me[s]["v1"])) for s in sids)
for v in sorted(set(tg[s]["v0"] for s in sids)): print(f"{v:>8} " + " ".join(f"{g}:{ct[(v, g)]}" for g in G if ct[(v, g)]))
print("\n不一致")
with open(os.path.join(W, "coding_merged_v1.csv"), "w", newline="") as fo:
    w = csv.writer(fo); w.writerow(["set", "sid", "v0", "v0_inf", "me", "me_also", "me_doc", "sonnet", "sonnet_also", "sonnet_doc"])
    for s in sids:
        w.writerow([tg[s]["set"], s, tg[s]["v0"], tg[s]["inf"], me[s]["v1"], me[s]["also"], me[s]["doc_ex"], so[s]["cat"], so[s].get("also", ""), so[s]["doc"]])
        if me[s]["v1"] != so[s]["cat"]: print(s, me[s]["v1"], so[s]["cat"], "|", me[s]["note"])
