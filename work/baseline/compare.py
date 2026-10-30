"""AIDev(エージェント PR)と ghhuman(人間 PR)の分類結果を並べる。
実行(humans_md/ で): uv run work/baseline/compare.py  → work/baseline/compare.txt
多数決(Opus/Sonnet/Haiku の 2/3 一致)は scripts/irr.py stats が書いた irr_merged.csv を使う。
"""
import collections, csv, json, os, random
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
out = []
P = lambda *a: out.append(" ".join(str(x) for x in a))
CATS = ["C1", "C2", "C3", "M", "H1", "H2", "H3", "H4", "H5", "BOT", "UNK", "NOAGREE"]

pops = {}
cr = pd.read_parquet(f"{ROOT}/outputs/aidev/human_blocks.parquet")
pops["aidev"] = collections.Counter("closed" if o == "closed" else "not_closed" for o in cr["outcome"])
gh = [json.loads(l) for l in open(f"{ROOT}/work/baseline/ghhuman_blocks.jsonl")]
pops["ghhuman"] = collections.Counter("closed" if r["outcome"] == "closed" else "not_closed" for r in gh if not r["agent_coauthor"])

D = {}
for name in ["aidev", "ghhuman"]:
    m = {r["sid"]: r for r in csv.DictReader(open(f"{ROOT}/outputs/{name}/irr/irr_merged.csv"))}
    st = {r["sid"]: r["stratum"] for r in json.load(open(f"{ROOT}/outputs/{name}/sample100.json"))}
    D[name] = (m, st)

P("== 母集団(層補正に使う件数)")
for k, v in pops.items():
    P(k, dict(v), "closed率 %.3f" % (v["closed"] / sum(v.values())))

P("\n== 多数決カテゴリ(100件中の件数)")
P("cat".ljust(8), "aidev", "ghhuman")
for c in CATS:
    P(c.ljust(8), sum(r["majority"] == c for r in D["aidev"][0].values()), sum(r["majority"] == c for r in D["ghhuman"][0].values()))


def wshare(m, st, pop, pred, ks):
    sc = collections.Counter(st[k] for k in m)
    w = lambda k: pop[st[k]] / sc[st[k]]
    return sum(w(k) for k in ks if pred(m[k])) / sum(w(k) for k in ks)


P("\n== 層補正後の比率(有効=BOT/UNK/NOAGREE除外, bootstrap 2000, seed 0)")
for name in D:
    m, st = D[name]; pop = pops[name]
    valid = [k for k in m if m[k]["majority"] not in ("BOT", "UNK", "NOAGREE")]
    for lab, pred in [("H系", lambda r: r["majority"].startswith("H")),
                      ("H1", lambda r: r["majority"] == "H1"), ("H2", lambda r: r["majority"] == "H2"),
                      ("H3", lambda r: r["majority"] == "H3"), ("H4/H5", lambda r: r["majority"] in ("H4", "H5")),
                      ("inferable=no", lambda r: r["majority_inf"] == "no"),
                      ("inferable=yes", lambda r: r["majority_inf"] == "yes")]:
        random.seed(0)
        bs = sorted(wshare(m, st, pop, pred, [random.choice(valid) for _ in valid]) for _ in range(2000))
        P(f" {name} {lab}: {wshare(m, st, pop, pred, valid):.3f} (95%CI {bs[50]:.3f}-{bs[1950]:.3f}) n_valid={len(valid)}")
    for g in ["closed", "not_closed"]:
        ss = [k for k in valid if st[k] == g]
        h = sum(m[k]["majority"].startswith("H") for k in ss)
        no = sum(m[k]["majority_inf"] == "no" for k in ss)
        P(f"   {g}: n={len(ss)} H={h} ({h / len(ss):.0%}) inferable=no {no} ({no / len(ss):.0%})")
    # Opus 単独・Sonnet 単独の H 率(重みなし)も
    for col in ["me_cat", "sonnet_cat", "haiku_cat"]:
        v = [k for k in m if m[k][col] not in ("BOT", "UNK")]
        P(f"   {col} 単独 H率(重みなし) {sum(m[k][col].startswith('H') for k in v)}/{len(v)}")

P("\n== 2群差(H系、層補正、独立 bootstrap 2000 の差の95%区間)")
random.seed(1)
diffs = []
for _ in range(2000):
    s = []
    for name in ["ghhuman", "aidev"]:
        m, st = D[name]; valid = [k for k in m if m[k]["majority"] not in ("BOT", "UNK", "NOAGREE")]
        s.append(wshare(m, st, pops[name], lambda r: r["majority"].startswith("H"), [random.choice(valid) for _ in valid]))
    diffs.append(s[0] - s[1])
diffs.sort(); P(f" ghhuman - aidev: 95%CI {diffs[50]:.3f} - {diffs[1950]:.3f}")

P("\n== 同一 repo の重なり")
cr["repo"] = cr["html_url"].str.split("github.com/").str[1].str.split("/pull/").str[0]
ga = set(cr["repo"].str.lower()); gr = collections.Counter(r["repo"].lower() for r in gh if not r["agent_coauthor"])
both = sorted(ga & set(gr))
P(" AIDev CR の repo 数", len(ga), " pilot 人間CR の repo 数", len(gr), " 共通", len(both))
for r in both:
    P(f"  {r}: AIDev CR {int((cr['repo'].str.lower() == r).sum())} / pilot 人間CR {gr[r]}")
# pilot の agent co-author PR への CR(別扱い)の規模
co = [r for r in gh if r["agent_coauthor"]]
P("\n== 参考: pilot の agent co-author trailer 付き PR への人間CR", len(co), dict(collections.Counter(r["outcome"] for r in co)))
open(f"{ROOT}/work/baseline/compare.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
