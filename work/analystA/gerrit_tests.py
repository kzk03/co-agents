"""理論担当の検証 T2/T3/T5/T6(Gerrit, LLM 不要)。
入力: work/analystA/cache.pkl(build_cache.py)、outputs/gerrit/gerrit_pilot_sample100.json、
      ラベル 非盲検 outputs/gerrit/irr/irr_merged.csv の majority、盲検 work/blind/blind_merged.csv の majority
H系 = majority が H*、C系 = C*/M。BOT/UNK/NOAGREE は除外。
CI はすべて bootstrap 2000 回(seed 0)。クラスタ = reviewer(主)/ project(副)。
実行(humans_md/ で): uv run python work/analystA/gerrit_tests.py > work/analystA/gerrit_tests.out
出力: 標準出力、work/analystA/gerrit_sample_features.csv
"""
import collections, csv, json, os, pickle, posixpath, random
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "work/analystA")
B = 2000
changes = pickle.load(open(os.path.join(OUT, "cache.pkl"), "rb"))
byid = {(c["p"], c["n"]): c for c in changes}

# ---------- 時点つき core ----------
core_since = {}            # (p, acc) -> 最初に CR±2 / WF+1 を出した日時(メッセージ履歴)
ever_lab = collections.defaultdict(set)   # a1 と同じ labels.all 由来(期間全体)
for c in changes:
    ever_lab[c["p"]] |= c["ever"]
    for acc, d, ps, cr, wf in c["votes"]:
        if cr in (2, -2) or wf == 1:
            k = (c["p"], acc)
            if k not in core_since or d < core_since[k]:
                core_since[k] = d
is_core_t = lambda p, acc, d: (p, acc) in core_since and core_since[(p, acc)] < d
is_core_ever = lambda p, acc: acc in ever_lab[p] or (p, acc) in core_since

# ---------- 母集団の -1/-2(非セルフ) ----------
neg = []
for c in changes:
    # ps ごとの人間・非 owner の CR 投票
    pos_ps = collections.defaultdict(set); neg_ps = collections.defaultdict(set)
    pos_ch, neg_ch = set(), set()
    for acc, d, ps, cr, wf in c["votes"]:
        if acc == c["owner"] or cr is None: continue
        if cr > 0: pos_ps[ps].add(acc); pos_ch.add(acc)
        if cr < 0: neg_ps[ps].add(acc); neg_ch.add(acc)
    for acc, d, ps, cr, wf in c["votes"]:
        if cr not in (-1, -2): continue
        if acc == c["owner"]: continue
        neg.append(dict(p=c["p"], n=c["n"], acc=acc, d=d, ps=ps, vote=cr, st=c["st"],
                        div_ps=bool(pos_ps[ps] - {acc}), div_ch=bool(pos_ch - {acc}),
                        core_t=is_core_t(c["p"], acc, d), core_e=is_core_ever(c["p"], acc)))
print(f"== 母集団 -1/-2(非セルフ、メッセージ履歴から再抽出) n={len(neg)}  -1 {sum(r['vote']==-1 for r in neg)}  -2 {sum(r['vote']==-2 for r in neg)}")
print("   (参考: gerrit_neg_votes_all.json は is_self 込み 31662 件)")


def cboot(rows, yf, gf, cf, seed=0):
    """クラスタ bootstrap: 群 True − 群 False の平均差。rows を cluster 単位で復元抽出。"""
    cl = collections.defaultdict(list)
    for r in rows: cl[cf(r)].append(r)
    keys = list(cl); rng = random.Random(seed); out = []
    for _ in range(B):
        s1 = s0 = n1 = n0 = 0
        for k in (rng.choice(keys) for _ in keys):
            for r in cl[k]:
                if gf(r): s1 += yf(r); n1 += 1
                else: s0 += yf(r); n0 += 1
        if n1 and n0: out.append(s1 / n1 - s0 / n0)
    a = [yf(r) for r in rows if gf(r)]; b = [yf(r) for r in rows if not gf(r)]
    if not a or not b or not out:
        return float("nan"), float("nan"), float("nan"), len(a), len(b), np.mean(a) if a else float("nan"), np.mean(b) if b else float("nan")
    return np.mean(a) - np.mean(b), np.percentile(out, 2.5), np.percentile(out, 97.5), len(a), len(b), np.mean(a), np.mean(b)


def fmt(res):
    d, lo, hi, na, nb, ma, mb = res
    return f"{ma:.3f}(n={na}) vs {mb:.3f}(n={nb}) 差 {d:+.3f} [{lo:+.3f},{hi:+.3f}]"


def or_ci(a, b, c, d):
    a, b, c, d = (x + 0.5 for x in (a, b, c, d)) if 0 in (a, b, c, d) else (a, b, c, d)
    lor = np.log(a * d / (b * c)); se = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    return np.exp(lor), np.exp(lor - 1.96 * se), np.exp(lor + 1.96 * se)


print("\n== T2 母集団: 時点つき core vs 期間全体 core")
for v in (-1, -2):
    rs = [r for r in neg if r["vote"] == v]
    ct = np.mean([r["core_t"] for r in rs]); ce = np.mean([r["core_e"] for r in rs])
    flip = sum(r["core_e"] and not r["core_t"] for r in rs)
    print(f" vote {v}: n={len(rs)} core比率 時点つき {ct:.3f} / 期間全体 {ce:.3f}  (期間全体では core だが投票時点ではまだ非 core: {flip} 件 = {flip/len(rs):.3f})")
    for key, nm in (("core_t", "時点つき"), ("core_e", "期間全体")):
        res = cboot(rs, lambda r: r["st"] == "ABANDONED", lambda r: r[key], lambda r: r["p"])
        print(f"   ABANDONED率 core vs 非core [{nm}] {fmt(res)} (project クラスタ)")

# ---------- サンプル ----------
smp = json.load(open(os.path.join(ROOT, "outputs/gerrit/gerrit_pilot_sample100.json")))
lab_nb = {r["sid"]: r["majority"] for r in csv.DictReader(open(os.path.join(ROOT, "outputs/gerrit/irr/irr_merged.csv")))}
lab_b = {r["sid"]: r["majority"] for r in csv.DictReader(open(os.path.join(ROOT, "work/blind/blind_merged.csv")))}
negidx = {(r["p"], r["n"], r["acc"], r["d"]): r for r in neg}
S = []
for s in smp:
    k = (s["project"], s["number"], int(s["reviewer"]), s["date"][:19])
    r = negidx.get(k)
    if r is None:
        print("unmatched", s["sid"], k); continue
    S.append(dict(sid=s["sid"], p=s["project"], n=s["number"], acc=int(s["reviewer"]), d=s["date"][:19], ps=s["ps"],
                  vote=int(s["vote"]), st=s["status"], nb=lab_nb.get(s["sid"], "UNK"), b=lab_b.get(s["sid"], "UNK"),
                  core_t=r["core_t"], core_e=r["core_e"], div_ps=r["div_ps"], div_ch=r["div_ch"]))
print(f"\n== サンプル照合 {len(S)}/100")
VALID = lambda m: m not in ("BOT", "UNK", "NOAGREE")
isH = lambda m: m.startswith("H")

print("\n== T2 サンプル: core/非core の H系比率(差 = core − 非core、reviewer クラスタ / project クラスタ)")
for lk, lname in (("nb", "非盲検"), ("b", "盲検")):
    for vsel, vname in ((lambda r: True, "-1/-2"), (lambda r: r["vote"] == -1, "-1のみ")):
        rs = [r for r in S if VALID(r[lk]) and vsel(r)]
        for key, nm in (("core_t", "時点つき"), ("core_e", "期間全体")):
            res = cboot(rs, lambda r: isH(r[lk]), lambda r: r[key], lambda r: r["acc"])
            res2 = cboot(rs, lambda r: isH(r[lk]), lambda r: r[key], lambda r: r["p"])
            a = sum(isH(r[lk]) for r in rs if r[key]); na = sum(r[key] for r in rs)
            c = sum(isH(r[lk]) for r in rs if not r[key]); nc = len(rs) - na
            o = or_ci(a, na - a, c, nc - c)
            print(f" [{lname} {vname} {nm}] core H {a}/{na} 非core H {c}/{nc} | {fmt(res)} | projクラスタ [{res2[1]:+.3f},{res2[2]:+.3f}] | OR {o[0]:.2f} ({o[1]:.2f}-{o[2]:.2f})")
    ch = [r["sid"] for r in S if r["core_e"] and not r["core_t"]]
    if lk == "nb": print(f"   定義で core 判定が変わるサンプル: {len(ch)} 件 {ch}")

print("\n== T3 divergence(同じ patchset に他の人間・非 owner の +1/+2 がある)")
for v in (-1, -2, None):
    rs = [r for r in neg if v is None or r["vote"] == v]
    print(f" 母集団 vote {v or '全'}: n={len(rs)} div_ps {np.mean([r['div_ps'] for r in rs]):.3f}  div_change {np.mean([r['div_ch'] for r in rs]):.3f}")
res = cboot(neg, lambda r: r["div_ps"], lambda r: r["vote"] == -2, lambda r: r["p"])
print(f" 母集団 -2 vs -1 の div_ps {fmt(res)} (project クラスタ)")
res = cboot([r for r in neg if r["vote"] == -1], lambda r: r["div_ps"], lambda r: r["core_t"], lambda r: r["p"])
print(f" 母集団 -1: core(時点) vs 非core の div_ps {fmt(res)} (project クラスタ)")
res = cboot(neg, lambda r: r["div_ps"], lambda r: r["st"] == "ABANDONED", lambda r: r["p"])
print(f" 母集団 ABANDONED vs それ以外 の div_ps {fmt(res)}")
for lk, lname in (("nb", "非盲検"), ("b", "盲検")):
    rs = [r for r in S if VALID(r[lk])]
    for key in ("div_ps", "div_ch"):
        res = cboot(rs, lambda r: r[key], lambda r: isH(r[lk]), lambda r: r["acc"])
        a = sum(r[key] for r in rs if isH(r[lk])); c = sum(r[key] for r in rs if not isH(r[lk]))
        print(f" [{lname}] {key}: H {a}/{sum(isH(r[lk]) for r in rs)} vs C {c}/{sum(not isH(r[lk]) for r in rs)} | {fmt(res)} (reviewer クラスタ)")
    m1 = [r for r in rs if r["vote"] == -1]
    res = cboot(m1, lambda r: r["div_ps"], lambda r: isH(r[lk]), lambda r: r["acc"])
    print(f"   -1のみ div_ps H vs C {fmt(res)}")
    sub = [r for r in rs if r[lk] in ("H2", "H4")]
    print(f"   H2/H4 のみ div_ps {sum(r['div_ps'] for r in sub)}/{len(sub)}; カテゴリ別 div_ps:",
          {cat: f"{sum(r['div_ps'] for r in rs if r[lk]==cat)}/{sum(r[lk]==cat for r in rs)}" for cat in sorted({r[lk] for r in rs})})


def gini(x):
    x = np.sort(np.asarray(x, float)); n = len(x)
    return (2 * np.sum(np.arange(1, n + 1) * x) / (n * x.sum())) - (n + 1) / n if n and x.sum() else float("nan")


def top10(x):
    x = np.sort(np.asarray(x, float))[::-1]; k = max(1, int(np.ceil(len(x) * 0.1)))
    return x[:k].sum() / x.sum()


def conc_boot(counts, seed=0):
    rng = np.random.default_rng(seed); x = np.asarray(counts)
    g = [gini(rng.choice(x, len(x))) for _ in range(B)]; t = [top10(rng.choice(x, len(x))) for _ in range(B)]
    return top10(x), np.percentile(t, [2.5, 97.5]), gini(x), np.percentile(g, [2.5, 97.5])


print("\n== T5 集中度(母集団、レビュアー × project ではなくアカウント単位、非セルフ)")
volneg = collections.Counter(r["acc"] for r in neg)
for v in (-1, -2):
    cnt = collections.Counter(r["acc"] for r in neg if r["vote"] == v)
    t, tci, g, gci = conc_boot(list(cnt.values()))
    print(f" vote {v}: 票 {sum(cnt.values())} レビュアー {len(cnt)} 上位10%占有 {t:.3f} [{tci[0]:.3f},{tci[1]:.3f}] Gini {g:.3f} [{gci[0]:.3f},{gci[1]:.3f}] 最大1人 {max(cnt.values())}")
thr = np.percentile(list(volneg.values()), 90)
print(f" 参考: レビュアー別 -1/-2 総数の上位10% 閾値 {thr:.0f} 票")
for lk, lname in (("nb", "非盲検"), ("b", "盲検")):
    rs = [r for r in S if VALID(r[lk])]
    for g in (True, False):
        cnt = collections.Counter(r["acc"] for r in rs if isH(r[lk]) == g)
        t, tci, gg, gci = conc_boot(list(cnt.values()))
        print(f" [{lname}] {'H' if g else 'C'}系 n={sum(cnt.values())} レビュアー {len(cnt)} 上位10%占有 {t:.3f} [{tci[0]:.3f},{tci[1]:.3f}] Gini {gg:.3f} [{gci[0]:.3f},{gci[1]:.3f}]")
    # 投票者の母集団での -1/-2 総数(ヘビー否定者か)
    res = cboot(rs, lambda r: np.log1p(volneg[r["acc"]]), lambda r: isH(r[lk]), lambda r: r["acc"])
    print(f"   投票者の母集団 -1/-2 総数 log1p 平均 H vs C {fmt(res)}; 中央値 H {np.median([volneg[r['acc']] for r in rs if isH(r[lk])]):.0f} C {np.median([volneg[r['acc']] for r in rs if not isH(r[lk])]):.0f}")
    res = cboot(rs, lambda r: volneg[r["acc"]] >= thr, lambda r: isH(r[lk]), lambda r: r["acc"])
    print(f"   投票者が上位10%ヘビー否定者 H vs C {fmt(res)}")

# ---------- T6 所有度 ----------
print("\n== T6 所有度(投票時点より前、同 project の他 change で、対象 patchset のファイル/ディレクトリに触れたもの)")
byproj = collections.defaultdict(list)
for c in changes: byproj[c["p"]].append(c)
first_seen = {p: min(c["created"] for c in cs) for p, cs in byproj.items()}
dirs = lambda fs: {posixpath.dirname(f) or "." for f in fs}
feat = []
for r in S:
    c0 = byid[(r["p"], r["n"])]
    F = set(c0["files"].get(r["ps"], [])); D = dirs(F)
    af = ad = rf = rd = ap = rp = 0
    for c in byproj[r["p"]]:
        if c["n"] == r["n"]: continue
        allf = set(x for fs in c["files"].values() for x in fs)
        hitf = bool(allf & F); hitd = bool(dirs(allf) & D)
        if c["owner"] == r["acc"] and c["created"] < r["d"]:
            ap += 1; af += hitf; ad += hitd
        if c["owner"] != r["acc"] and any(a == r["acc"] and d < r["d"] for a, d in c["msgs"]):
            rp += 1; rf += hitf; rd += hitd
    feat.append(dict(r, nfiles=len(F), auth_file=af, auth_dir=ad, rev_file=rf, rev_dir=rd, auth_proj=ap, rev_proj=rp,
                     own_file=af + rf, own_dir=ad + rd, data_start=first_seen[r["p"]][:10]))
for lk, lname in (("nb", "非盲検"), ("b", "盲検")):
    rs = [r for r in feat if VALID(r[lk])]
    print(f" [{lname}] n={len(rs)} (H {sum(isH(r[lk]) for r in rs)})")
    for key in ("auth_file", "rev_file", "own_file", "own_dir", "auth_proj", "rev_proj"):
        res = cboot(rs, lambda r: np.log1p(r[key]), lambda r: isH(r[lk]), lambda r: r["acc"])
        res2 = cboot(rs, lambda r: r[key] > 0, lambda r: isH(r[lk]), lambda r: r["acc"])
        mh = np.median([r[key] for r in rs if isH(r[lk])]); mc = np.median([r[key] for r in rs if not isH(r[lk])])
        print(f"   {key:9s} 中央値 H {mh:.0f} C {mc:.0f} | log1p {fmt(res)} | >0 の割合 {fmt(res2)}")
    # ファイル所有度を中央値で二分した H 率(project 内経験の大小で交絡するので rev_proj も見る)
    med = np.median([r["own_file"] for r in rs])
    hi = [isH(r[lk]) for r in rs if r["own_file"] > med]; lo = [isH(r[lk]) for r in rs if r["own_file"] <= med]
    print(f"   own_file > 中央値{med:.0f}: H {sum(hi)}/{len(hi)}  ≤: H {sum(lo)}/{len(lo)}")
    # 比率指標: ファイル関与 / project 関与(経験量で正規化)
    res = cboot([r for r in rs if r["auth_proj"] + r["rev_proj"] > 0],
                lambda r: r["own_file"] / (r["auth_proj"] + r["rev_proj"]), lambda r: isH(r[lk]), lambda r: r["acc"])
    print(f"   ファイル関与/project関与 の比 {fmt(res)}")
print(" データ開始日(サンプル project の最古 change)中央値:", sorted(r["data_start"] for r in feat)[len(feat) // 2],
      " 投票日がデータ開始から1年未満のサンプル:", sum(int(r["d"][:4]) - int(r["data_start"][:4]) < 1 for r in feat))
with open(os.path.join(OUT, "gerrit_sample_features.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(feat[0])); w.writeheader(); w.writerows(feat)

# ---------- 感度分析: データ窓の左打ち切り(多くの project で 2019 年以前の change が疎) ----------
print("\n== 感度: 投票日 >= 2021-01-01 に限定(core_since の左打ち切りを緩和)")
yr = collections.Counter(c["created"][:4] for c in changes)
print(" 全 change の作成年分布:", sorted(yr.items()))
for v in (-1, -2):
    rs = [r for r in neg if r["vote"] == v and r["d"] >= "2021"]
    flip = sum(r["core_e"] and not r["core_t"] for r in rs)
    print(f" 母集団 vote {v} (2021-): n={len(rs)} core 時点つき {np.mean([r['core_t'] for r in rs]):.3f} / 期間全体 {np.mean([r['core_e'] for r in rs]):.3f} 食い違い {flip/len(rs):.3f}")
    rs0 = [r for r in neg if r["vote"] == v and r["d"] < "2021"]
    print(f"   (参考 -2020: n={len(rs0)} 食い違い {sum(r['core_e'] and not r['core_t'] for r in rs0)/len(rs0):.3f})")
for lk, lname in (("nb", "非盲検"), ("b", "盲検")):
    rs = [r for r in S if VALID(r[lk]) and r["d"] >= "2021"]
    for key, nm in (("core_t", "時点つき"), ("core_e", "期間全体")):
        res = cboot(rs, lambda r: isH(r[lk]), lambda r: r[key], lambda r: r["acc"])
        print(f" [{lname} 2021- {nm}] core vs 非core H率 {fmt(res)}")
    res = cboot(rs, lambda r: r["div_ps"], lambda r: isH(r[lk]), lambda r: r["acc"])
    print(f" [{lname} 2021-] div_ps H vs C {fmt(res)}")
    fr = [r for r in feat if VALID(r[lk]) and r["d"] >= "2021"]
    res = cboot(fr, lambda r: np.log1p(r["own_file"]), lambda r: isH(r[lk]), lambda r: r["acc"])
    print(f" [{lname} 2021-] own_file log1p H vs C {fmt(res)}")
