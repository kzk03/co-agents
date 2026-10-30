"""B2: CR 後の経過を LLM なしで 4 分類し、v0(H/C)・v1(C/K/R/D)別に集計する。
入力: outputs/{aidev,ghhuman}/sample100.json, irr/irr_merged.csv, work/codebook/coding_merged_v1.csv,
      work/analystB/b2_prs.jsonl(fetch_b2.py、gh の現在状態), data/aidev/*.parquet, work/explore/cache_gh/prs.jsonl,
      data/pilot_raw_full/*/prs_full.jsonl(スナップショットとの突合)
分類(CR 時刻 t 以降、PR 単位の現在状態):
  a  merged(サブ: t 以降のコミットあり a1 / なし a0)
  d  open のまま、または close した主体が Bot(stale 等)・エージェント自身
  c  人間が close。t〜close+10分 に、PR 作者以外の人間のコメント/レビュー(当該 CR 自身は除く)がある、
     または t 以降に作られた Issue からの cross-reference がある
  b  人間が close。上の c の条件なし
重み: 層(closed / not_closed、スナップショットの結末)ごとの母集団件数 / 標本件数
出力: work/analystB/b2_rows.csv, 標準出力(b2.out に保存)
uv run python work/analystB/b2_analyze.py > work/analystB/b2.out"""
import collections, csv, json, os, random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
B = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(B, "../.."))
P = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/pilot_raw_full"))
T = lambda s: datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
BOTS = {"copilot", "copilot-swe-agent", "github-actions", "stale", "openai-codex", "devin-ai-integration", "google-labs-jules"}
isbot = lambda a: a is None and False or (a is not None and (a.get("__typename") == "Bot" or (a.get("login") or "").lower().endswith("[bot]") or (a.get("login") or "").lower() in BOTS))

gh = {}
for l in open(os.path.join(B, "b2_prs.jsonl")):
    j = json.loads(l)
    if j["ok"] or (j["repo"], j["number"]) not in gh:
        gh[(j["repo"], j["number"])] = j
v1 = {r["sid"]: r for r in csv.DictReader(open(os.path.join(ROOT, "work/codebook/coding_merged_v1.csv")))}
prq = pd.read_parquet(os.path.join(ROOT, "data/aidev/pull_request.parquet")).set_index("id")
rvq = pd.read_parquet(os.path.join(ROOT, "data/aidev/pr_reviews.parquet")).set_index("id")
cmq = pd.read_parquet(os.path.join(ROOT, "data/aidev/pr_comments.parquet"))
prev = {j["pr_id"]: j for j in map(json.loads, open(os.path.join(ROOT, "work/explore/cache_gh/prs.jsonl"))) if j["ok"]}
pilot = {}

def pilot_pr(repo, n):
    if repo not in pilot:
        d = {}
        for l in open(os.path.join(P, repo.replace("/", "__"), "prs_full.jsonl")):
            try: j = json.loads(l)
            except Exception: continue
            d[j["number"]] = j
        pilot[repo] = d
    return pilot[repo].get(n)

def grp_v1(c):
    return c.split("-")[0] if c[:1] in "KRD" else ("C" if c[:1] in "CM" else c)

rows = []
for name in ("aidev", "ghhuman"):
    maj = {r["sid"]: r["majority"] for r in csv.DictReader(open(os.path.join(ROOT, f"outputs/{name}/irr/irr_merged.csv")))}
    for s in json.load(open(os.path.join(ROOT, f"outputs/{name}/sample100.json"))):
        sid = s["sid"]
        if name == "aidev":
            n = int(s["html_url"].rstrip("/").split("/")[-1]); t = str(rvq.loc[int(s["review_id"]), "submitted_at"])
            t = pd.Timestamp(t).strftime("%Y-%m-%dT%H:%M:%S"); author = str(prq.loc[int(s["pr_id"]), "user"])
        else:
            n = int(s["number"]); t = s["submittedAt"]; author = s["pr_author"]
        tt = T(t); g = gh.get((s["repo"], n)) or {}; p = g.get("pr")
        v0 = maj.get(sid, "")
        v0g = "H" if v0.startswith("H") else ("C" if v0[:1] in "CM" else "other")
        v1c = v1[sid]["me"] if sid in v1 else (v0 if v0g == "C" else "")
        r = dict(set=name, sid=sid, repo=s["repo"], number=n, t=t, stratum=s["stratum"], snap_outcome=s["outcome"], v0=v0, v0g=v0g,
                 v1=v1c, v1g=grp_v1(v1c) if v1c else "other", src="gh")
        if p:
            st = "merged" if p["merged"] else p["state"].lower()
            ce = [x for x in p["timelineItems"]["nodes"] if x["__typename"] == "ClosedEvent"]
            closer = ce[-1]["actor"] if ce else None
            closed_at = p["closedAt"]
            commits = [x["commit"]["committedDate"] for x in p["commits"]["nodes"]]
            alogin = (p["author"] or {}).get("login") or author
            evs = [(x["createdAt"], x["author"], "comment", x["body"]) for x in p["comments"]["nodes"]]
            evs += [(x["submittedAt"], x["author"], "review:" + x["state"], x["body"]) for x in p["reviews"]["nodes"] if x["submittedAt"]]
            xref_issue = any(x["__typename"] == "CrossReferencedEvent" and (x.get("source") or {}).get("__typename") == "Issue"
                             and T(x["source"]["createdAt"]) > tt for x in p["timelineItems"]["nodes"])
            size = (p["additions"] or 0) + (p["deletions"] or 0); closer_login = (closer or {}).get("login")
            closer_bot = closer is not None and (isbot(closer) or closer_login == alogin and isbot(p["author"]))
        else:  # repo 消失: AIDev スナップショットで代替(close した人は不明 → 人間とみなす)
            r["src"] = "snapshot"; q = prq.loc[int(s["pr_id"])]
            st = "merged" if q["merged_at"] is not None and str(q["merged_at"]) != "None" else q["state"]
            closed_at = None if q["closed_at"] is None else pd.Timestamp(q["closed_at"]).strftime("%Y-%m-%dT%H:%M:%SZ")
            commits = (prev.get(int(s["pr_id"])) or {}).get("commits", []); alogin = author
            cm = cmq[cmq.pr_id == int(s["pr_id"])]
            evs = [(pd.Timestamp(x.created_at).strftime("%Y-%m-%dT%H:%M:%SZ"), {"login": x.user, "__typename": "Bot" if x.user_type == "Bot" else "User"}, "comment", x.body) for x in cm.itertuples()]
            xref_issue = False; size = None; closer_login = None; closer_bot = False
        commit_after = any(T(c) > tt for c in commits)
        rev_login = s["reviewer"]
        def human_other(e):
            ts, a, kind, body = e
            if isbot(a) or (a or {}).get("login") == alogin: return False
            if T(ts) <= tt + timedelta(seconds=1) and (a or {}).get("login") == rev_login and kind.startswith("review"): return False  # 当該 CR
            return T(ts) > tt
        upto = (T(closed_at) + timedelta(minutes=10)) if closed_at else None
        after = [e for e in evs if human_other(e) and (upto is None or T(e[0]) <= upto)]
        if st == "merged":
            cls = "a"; sub = "a1" if commit_after else "a0"
        elif st == "open":
            cls = "d"; sub = "d_open"
        elif closer_bot:
            cls = "d"; sub = "d_botclose"
        else:
            if after or xref_issue:
                cls = "c"; sub = "c_issue" if (xref_issue and not after) else "c_comment"
            else:
                cls = "b"; sub = "b"
            sub += "_byauthor" if closer_login and closer_login == alogin else ""
        r.update(state_now=st, cls=cls, sub=sub, commit_after=commit_after, n_human_after=len(after), xref_issue=xref_issue,
                 closer=closer_login, size=size)
        if name == "ghhuman":
            pp = pilot_pr(s["repo"], n)
            r["pilot_commit_after"] = None if pp is None else any(T(c["commit"]["committedDate"]) > tt for c in (pp.get("commits") or {}).get("nodes", []))
        else:
            pv = prev.get(int(s["pr_id"]))
            r["pilot_commit_after"] = None if pv is None else any(T(c) > tt for c in pv["commits"])
        rows.append(r)
with open(os.path.join(B, "b2_rows.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

# 母集団の層件数
hb = pd.read_parquet(os.path.join(ROOT, "outputs/aidev/human_blocks.parquet"))
POP = {"aidev": collections.Counter("closed" if o == "closed" else "not_closed" for o in hb.outcome)}
POP["ghhuman"] = collections.Counter("closed" if j["outcome"] == "closed" else "not_closed"
                                     for j in map(json.loads, open(os.path.join(ROOT, "work/baseline/ghhuman_blocks.jsonl"))) if not j["agent_coauthor"])
NS = {nm: collections.Counter(r["stratum"] for r in rows if r["set"] == nm) for nm in POP}
W = {nm: {k: POP[nm][k] / NS[nm][k] for k in NS[nm]} for nm in POP}
print("母集団層", {k: dict(v) for k, v in POP.items()}, "重み", {k: {a: round(b, 1) for a, b in v.items()} for k, v in W.items()})
print("取得元", collections.Counter((r["set"], r["src"]) for r in rows))
print("スナップショット結末 → 現在の状態", collections.Counter((r["set"], r["snap_outcome"], r["state_now"]) for r in rows))
cc = [(r["commit_after"], r["pilot_commit_after"]) for r in rows if r["pilot_commit_after"] is not None]
print("CR後コミット gh 現在 vs 既存キャッシュ/pilot 一致", sum(a == b for a, b in cc), "/", len(cc))
CL = ["a", "b", "c", "d"]

def wprop(ss, nm, f):
    w = np.array([W[nm][r["stratum"]] for r in ss]); x = np.array([f(r) for r in ss], float)
    return (w * x).sum() / w.sum() if len(ss) else float("nan")

def boot(ss_a, ss_b, nm, f, B_=2000, seed=0, cluster=False):
    """層内リサンプル(cluster=True なら repo 単位)。差 a−b の重み付き比率の 95%CI"""
    rnd = random.Random(seed); out = []
    def res(ss):
        if cluster:
            reps = sorted({r["repo"] for r in ss}); by = collections.defaultdict(list)
            for r in ss: by[r["repo"]].append(r)
            return [x for _ in reps for x in by[rnd.choice(reps)]]
        o = []
        for k in ("closed", "not_closed"):
            s = [r for r in ss if r["stratum"] == k]; o += [rnd.choice(s) for _ in s]
        return o
    for _ in range(B_):
        a, b = res(ss_a), res(ss_b)
        if a and b: out.append(wprop(a, nm, f) - wprop(b, nm, f))
    out.sort(); return out[int(len(out) * .025)], out[int(len(out) * .975)]

def table(nm, key, levels, label):
    ss0 = [r for r in rows if r["set"] == nm]
    print(f"\n== {nm} {label}(各行: n / 標本比率 a,b,c,d / 重み付き a,b,c,d / サブ分類)")
    for g in levels:
        ss = [r for r in ss0 if r[key] == g]
        if not ss: continue
        raw = [np.mean([r["cls"] == c for r in ss]) for c in CL]
        wt = [wprop(ss, nm, lambda r, c=c: r["cls"] == c) for c in CL]
        print(f" {g:7} n={len(ss):3} 標本 " + " ".join(f"{c}={v:.2f}" for c, v in zip(CL, raw)) + " | 重み付き " + " ".join(f"{c}={v:.2f}" for c, v in zip(CL, wt))
              + " | " + str(dict(collections.Counter(r["sub"] for r in ss))))

for nm in ("aidev", "ghhuman", "both"):
    pass
for nm in ("aidev", "ghhuman"):
    table(nm, "v0g", ["H", "C", "other"], "v0(多数決) H/C")
    table(nm, "v1g", ["C", "K", "R", "D", "X"], "v1 群(C は v1 の C + v0 多数決 C)")
    table(nm, "v1", ["K-pub", "K-priv", "R-tech", "R-gov", "D-dir", "D-risk"], "v1 細分類")

print("\n== H−C の差(重み付き、95%CI: 層内 bootstrap / repo クラスタ bootstrap)")
DEFS = {"a(merged)": lambda r: r["cls"] == "a", "b": lambda r: r["cls"] == "b", "c": lambda r: r["cls"] == "c", "d": lambda r: r["cls"] == "d",
        "b+c(人間close)": lambda r: r["cls"] in "bc", "CR後コミット": lambda r: r["commit_after"]}
for nm in ("aidev", "ghhuman"):
    for ga, gb, key in (("H", "C", "v0g"), ("D", "C", "v1g"), ("R", "C", "v1g"), ("K", "C", "v1g")):
        A = [r for r in rows if r["set"] == nm and r[key] == ga]; Bb = [r for r in rows if r["set"] == nm and r[key] == gb]
        for dn, f in DEFS.items():
            d = wprop(A, nm, f) - wprop(Bb, nm, f)
            lo, hi = boot(A, Bb, nm, f); clo, chi = boot(A, Bb, nm, f, cluster=True, seed=1)
            print(f" {nm:7} {ga}−{gb} (n={len(A)},{len(Bb)}) {dn:14} {d:+.3f} CI[{lo:+.3f},{hi:+.3f}] repoCI[{clo:+.3f},{chi:+.3f}]")

print("\n== a12 との突合(ghhuman、v0 H/C、標本比率・重みなし、スナップショット結末)")
for g in ("H", "C"):
    ss = [r for r in rows if r["set"] == "ghhuman" and r["v0g"] == g]
    print(f" {g} n={len(ss)} snapshot closed {np.mean([r['snap_outcome']=='closed' for r in ss]):.2f} 現在 b+c {np.mean([r['cls'] in 'bc' for r in ss]):.2f} "
          f"CR後コミット(pilot) {np.mean([bool(r['pilot_commit_after']) for r in ss]):.2f}")
print("== 同じことを aidev で")
for g in ("H", "C"):
    ss = [r for r in rows if r["set"] == "aidev" and r["v0g"] == g]
    print(f" {g} n={len(ss)} snapshot closed {np.mean([r['snap_outcome']=='closed' for r in ss]):.2f} 現在 b+c {np.mean([r['cls'] in 'bc' for r in ss]):.2f} CR後コミット {np.mean([r['commit_after'] for r in ss]):.2f}")

print("\n== 層内(スナップショット結末の層ごと)で H/C を比較(層化抽出の影響を除く)")
for nm in ("aidev", "ghhuman"):
    for k in ("closed", "not_closed"):
        for g in ("H", "C"):
            ss = [r for r in rows if r["set"] == nm and r["stratum"] == k and r["v0g"] == g]
            print(f" {nm:7} {k:10} {g} n={len(ss):2} " + str(dict(sorted(collections.Counter(r['sub'] for r in ss).items()))))

print("\n== 交絡: PR サイズ(追加+削除行、全体の三分位)で層別した b+c 率(重み付き)、Mantel-Haenszel 型の重み付き差")
for nm in ("aidev", "ghhuman"):
    ss0 = [r for r in rows if r["set"] == nm and r["v0g"] in "HC" and r["v0g"] != "" and r["size"] is not None]
    q = np.quantile([r["size"] for r in ss0], [1 / 3, 2 / 3]); print(f" {nm} 三分位境界 {q.round(0).tolist()}")
    num = den = 0
    for lo, hi, lab in ((-1, q[0], "小"), (q[0], q[1], "中"), (q[1], 1e12, "大")):
        s = [r for r in ss0 if lo < r["size"] <= hi]
        h = [r for r in s if r["v0g"] == "H"]; c = [r for r in s if r["v0g"] == "C"]
        if h and c:
            d = wprop(h, nm, DEFS["b+c(人間close)"]) - wprop(c, nm, DEFS["b+c(人間close)"]); wgt = len(h) * len(c) / (len(h) + len(c))
            num += d * wgt; den += wgt
        print(f"   {lab} H n={len(h)} b+c {wprop(h, nm, DEFS['b+c(人間close)']):.2f} | C n={len(c)} b+c {wprop(c, nm, DEFS['b+c(人間close)']):.2f}")
    print(f"   サイズ層別の重み付き差 H−C {num/den:+.3f}")
    # H と C の PR サイズ中央値
    print(f"   サイズ中央値 H {np.median([r['size'] for r in ss0 if r['v0g']=='H']):.0f} C {np.median([r['size'] for r in ss0 if r['v0g']=='C']):.0f}")

print("\n== 交絡: repo(H と C の両方を含む repo に限定 / repo ごとに1件に間引き 200 回平均)")
for nm in ("aidev", "ghhuman"):
    ss0 = [r for r in rows if r["set"] == nm and r["v0g"] in ("H", "C")]
    by = collections.defaultdict(list)
    for r in ss0: by[r["repo"]].append(r)
    both = [r for rp, l in by.items() if {x["v0g"] for x in l} == {"H", "C"} for r in l]
    h = [r for r in both if r["v0g"] == "H"]; c = [r for r in both if r["v0g"] == "C"]
    if h and c:
        print(f" {nm} 両方ある repo {len({r['repo'] for r in both})} 件、H n={len(h)} b+c {wprop(h, nm, DEFS['b+c(人間close)']):.2f} / C n={len(c)} b+c {wprop(c, nm, DEFS['b+c(人間close)']):.2f}")
    else:
        print(f" {nm} 両方ある repo なし")
    rnd = random.Random(3); ds = []
    for _ in range(200):
        one = [rnd.choice(l) for l in by.values()]
        h = [r for r in one if r["v0g"] == "H"]; c = [r for r in one if r["v0g"] == "C"]
        if h and c: ds.append(wprop(h, nm, DEFS["b+c(人間close)"]) - wprop(c, nm, DEFS["b+c(人間close)"]))
    print(f" {nm} repo 1件間引き(repo 数 {len(by)})H−C b+c 差 平均 {np.mean(ds):+.3f}(200 回の 2.5–97.5% {np.quantile(ds, .025):+.3f}..{np.quantile(ds, .975):+.3f})")
