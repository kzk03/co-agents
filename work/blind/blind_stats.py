"""Gerrit 盲検再コード vs 非盲検の比較(scripts/irr.py stats 相当。共有出力は書き換えない)。

使い方(humans_md/ で): uv run python work/blind/blind_stats.py
入力:
  盲検  Opus   work/blind/coding_opus_blind.csv(blind 担当がダンプだけを見て分類)
        Sonnet outputs/gerrit_blind/irr/sonnet_batch0-2.jsonl + work/blind/sonnet_batch3.jsonl(共有側の batch3 が空だったため再実行)
        Haiku  outputs/gerrit_blind/irr/haiku_batch*.jsonl
  非盲検 outputs/gerrit/irr/irr_merged.csv(me_cat=Opus 手作業, sonnet_cat, haiku_cat, majority)
  GitHub outputs/aidev/irr/irr_merged.csv(大小比較用)
出力: 標準出力、work/blind/blind_merged.csv, work/blind/blind_vs_nonblind.csv
"""
import collections, csv, glob, importlib.util, json, math, os, random

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("irr", os.path.join(ROOT, "scripts", "irr.py"))
irr = importlib.util.module_from_spec(spec); spec.loader.exec_module(irr)


def jl(files):
    d = {}
    for f in files:
        for l in open(f):
            if l.strip().startswith("{"):
                j = json.loads(l); d[j["sid"]] = j
    return d


B = os.path.join(ROOT, "outputs/gerrit_blind/irr")
blind = {
    "opus": {r["sid"]: r for r in csv.DictReader(open(os.path.join(HERE, "coding_opus_blind.csv")))},
    "sonnet": jl([os.path.join(B, f"sonnet_batch{i}.jsonl") for i in range(3)] + [os.path.join(HERE, "sonnet_batch3.jsonl")]),
    "haiku": jl(sorted(glob.glob(os.path.join(B, "haiku_batch*.jsonl")))),
}
nb_rows = {r["sid"]: r for r in csv.DictReader(open(os.path.join(ROOT, "outputs/gerrit/irr/irr_merged.csv")))}
nonblind = {m: {k: {"cat": r[f"{c}_cat"], "inferable": r[f"{c}_inf"]} for k, r in nb_rows.items()}
            for m, c in [("opus", "me"), ("sonnet", "sonnet"), ("haiku", "haiku")]}
sids = sorted(set(nb_rows) & set(blind["opus"]) & set(blind["sonnet"]) & set(blind["haiku"]))
print("n items", len(sids), {m: len(d) for m, d in blind.items()})

grp = lambda c: "H" if c.startswith("H") else ("C" if c[0] in "CM" else c)


def majority(codes):
    m = {}
    for k in sids:
        top = collections.Counter(codes[x][k]["cat"] for x in ("opus", "sonnet", "haiku")).most_common(1)[0]
        m[k] = top[0] if top[1] >= 2 else "NOAGREE"
    return m


maj_b = majority(blind)
maj_nb = {k: nb_rows[k]["majority"] for k in sids}
assert maj_nb == majority(nonblind), "non-blind majority mismatch"

# 層(投票×時期)と投票値
s = irr.paths("gerrit")
pop, st = irr.strata("gerrit", s)
smp = {r["sid"]: r for r in json.load(open(os.path.join(s["dir"], s["sample"])))}
vote = {k: smp[k]["vote"] for k in sids}
scnt = collections.Counter(st[k] for k in sids)
W = lambda k: pop[st[k]] / scnt[st[k]]


def share(ss, lab):
    den = sum(W(k) for k in ss)
    return sum(W(k) for k in ss if lab[k].startswith("H")) / den


def est(lab, exclude=("BOT", "UNK", "NOAGREE")):
    """irr.py stats と同じ:valid 全体から復元抽出(seed 0, 2000回)+ 層内ブートストラップ"""
    valid = [k for k in sids if lab[k] not in exclude]
    random.seed(0)
    bs = sorted(share([random.choice(valid) for _ in valid], lab) for _ in range(2000))
    byst = collections.defaultdict(list)
    for k in valid:
        byst[st[k]].append(k)
    random.seed(1)
    bs2 = sorted(share([random.choice(v) for v in byst.values() for _ in v], lab) for _ in range(2000))
    return share(valid, lab), bs[50], bs[1950], bs2[50], bs2[1950], len(valid), bs


def wilson(x, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = x / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


print("\n== 層補正 H系比率(多数決、BOT/UNK/NOAGREE 除外)")
res = {}
for nm, lab in [("nonblind", maj_nb), ("blind", maj_b)]:
    e = est(lab); res[nm] = e
    print(f"{nm:9s} valid={e[5]} H={e[0]:.3f} 95%CI(irr.py式) {e[1]:.3f}-{e[2]:.3f}  層内bootstrap {e[3]:.3f}-{e[4]:.3f}")
print("多数決分布 nonblind", dict(sorted(collections.Counter(maj_nb.values()).items())))
print("多数決分布 blind   ", dict(sorted(collections.Counter(maj_b.values()).items())))

print("\n== コーダー別 層補正 H系比率(各コーダー単独、BOT/UNK 除外)")
for m in ("opus", "sonnet", "haiku"):
    out = []
    for nm, d in [("nonblind", nonblind), ("blind", blind)]:
        lab = {k: d[m][k]["cat"] for k in sids}
        e = est(lab)
        out.append(f"{nm} {e[0]:.3f} ({e[1]:.3f}-{e[2]:.3f}, valid={e[5]})")
    print(f"{m:6s}", " | ".join(out))

print("\n== 投票値別 H系(多数決、valid のみ、Wilson 95%CI)")
for v in sorted(set(vote.values())):
    for nm, lab in [("nonblind", maj_nb), ("blind", maj_b)]:
        ss = [k for k in sids if vote[k] == v and lab[k] not in ("BOT", "UNK", "NOAGREE")]
        x = sum(lab[k].startswith("H") for k in ss); lo, hi = wilson(x, len(ss))
        allv = [k for k in sids if vote[k] == v]
        print(f"vote {v} {nm:9s} H {x}/{len(ss)} = {x / len(ss):.3f} (Wilson {lo:.3f}-{hi:.3f})  [全{len(allv)}件, 除外 {len(allv) - len(ss)}]")
    for m in ("opus", "sonnet", "haiku"):
        row = []
        for nm, d in [("nonblind", nonblind), ("blind", blind)]:
            ss = [k for k in sids if vote[k] == v and d[m][k]["cat"] not in ("BOT", "UNK")]
            x = sum(d[m][k]["cat"].startswith("H") for k in ss)
            row.append(f"{nm} {x}/{len(ss)}")
        print(f"   {m:6s}", "  ".join(row))

print("\n== -2 の項目ごとの多数決(nonblind → blind)と各コーダー")
for k in sids:
    if vote[k] == -2:
        print(k, maj_nb[k], "->", maj_b[k], " | nb", [nonblind[m][k]["cat"] for m in ("opus", "sonnet", "haiku")],
              " b", [blind[m][k]["cat"] for m in ("opus", "sonnet", "haiku")])

print("\n== カテゴリの入れ替わり(nonblind → blind)")
for m in ("opus", "sonnet", "haiku", "majority"):
    a = maj_nb if m == "majority" else {k: nonblind[m][k]["cat"] for k in sids}
    b = maj_b if m == "majority" else {k: blind[m][k]["cat"] for k in sids}
    same = sum(a[k] == b[k] for k in sids); sg = sum(grp(a[k]) == grp(b[k]) for k in sids)
    flips = collections.Counter(f"{grp(a[k])}->{grp(b[k])}" for k in sids if grp(a[k]) != grp(b[k]))
    po, kc = irr.kappa([a[k] for k in sids], [b[k] for k in sids])
    pg, kg = irr.kappa([grp(a[k]) for k in sids], [grp(b[k]) for k in sids])
    f2 = collections.Counter(f"{grp(a[k])}->{grp(b[k])}" for k in sids if grp(a[k]) != grp(b[k]) and vote[k] == -2)
    print(f"{m:8s} cat一致 {same}/100 (κ {kc:.2f})  group一致 {sg}/100 (κ {kg:.2f})  group変化 {dict(flips)}  うち-2 {dict(f2)}")

print("\n== コーダー間 κ(cat / C-H group / inferable)po/κ")
for nm, d in [("nonblind", nonblind), ("blind", blind)]:
    for lab, f in [("cat", lambda x: x["cat"]), ("group", lambda x: grp(x["cat"])), ("inferable", lambda x: x["inferable"])]:
        A, Bq, C = ([f(d[m][k]) for k in sids] for m in ("opus", "sonnet", "haiku"))
        print(f"{nm:9s} {lab:9s} opus-sonnet %.2f/%.2f opus-haiku %.2f/%.2f sonnet-haiku %.2f/%.2f fleiss %.2f" %
              (*irr.kappa(A, Bq), *irr.kappa(A, C), *irr.kappa(Bq, C), irr.fleiss(list(zip(A, Bq, C)))))

# GitHub との比較(差のブートストラップ)
print("\n== Gerrit(盲検/非盲検) − GitHub(AIDev)")
a = irr.paths("aidev")
apop, ast = irr.strata("aidev", a)
arows = {r["sid"]: r for r in csv.DictReader(open(os.path.join(ROOT, "outputs/aidev/irr/irr_merged.csv")))}
amaj = {k: r["majority"] for k, r in arows.items()}
asids = list(arows); acnt = collections.Counter(ast[k] for k in asids)
aW = lambda k: apop[ast[k]] / acnt[ast[k]]
avalid = [k for k in asids if amaj[k] not in ("BOT", "UNK", "NOAGREE")]
ash = lambda ss: sum(aW(k) for k in ss if amaj[k].startswith("H")) / sum(aW(k) for k in ss)
random.seed(0)
abs_ = sorted(ash([random.choice(avalid) for _ in avalid]) for _ in range(2000))
print(f"GitHub H={ash(avalid):.3f} (95%CI {abs_[50]:.3f}-{abs_[1950]:.3f}, valid={len(avalid)})")
for nm in ("nonblind", "blind"):
    lab = maj_nb if nm == "nonblind" else maj_b
    valid = [k for k in sids if lab[k] not in ("BOT", "UNK", "NOAGREE")]
    random.seed(2); diffs = []
    for _ in range(2000):
        g = share([random.choice(valid) for _ in valid], lab)
        h = ash([random.choice(avalid) for _ in avalid])
        diffs.append(g - h)
    diffs.sort()
    print(f"{nm:9s} diff={res[nm][0] - ash(avalid):+.3f} 95%CI {diffs[50]:+.3f}~{diffs[1950]:+.3f}  P(diff<=0)={sum(x <= 0 for x in diffs) / 2000:.4f}")

with open(os.path.join(HERE, "blind_merged.csv"), "w") as fo:
    w = csv.writer(fo)
    w.writerow(["sid", "vote", "stratum", "opus_cat", "sonnet_cat", "haiku_cat", "majority",
                "opus_inf", "sonnet_inf", "haiku_inf"])
    for k in sids:
        w.writerow([k, vote[k], "/".join(map(str, st[k])), *[blind[m][k]["cat"] for m in ("opus", "sonnet", "haiku")], maj_b[k],
                    *[blind[m][k]["inferable"] for m in ("opus", "sonnet", "haiku")]])
with open(os.path.join(HERE, "blind_vs_nonblind.csv"), "w") as fo:
    w = csv.writer(fo)
    w.writerow(["sid", "vote", "nb_majority", "b_majority", "nb_opus", "b_opus", "nb_sonnet", "b_sonnet", "nb_haiku", "b_haiku"])
    for k in sids:
        w.writerow([k, vote[k], maj_nb[k], maj_b[k], *[x for m in ("opus", "sonnet", "haiku") for x in (nonblind[m][k]["cat"], blind[m][k]["cat"])]])
