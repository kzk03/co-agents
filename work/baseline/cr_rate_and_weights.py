"""(a) repo ごとの CR 使用率 = 人間 CR / 人間レビュー(人間作者 PR、ボット除外。COMMENTED/APPROVED/CHANGES_REQUESTED/DISMISSED 全部が分母)
   pilot は review_bodies、AIDev は pr_reviews(user_type=User、ボット名除外)
(b) repo 構成の感度分析: 重み = 母集団件数(層×repo群)/サンプル件数(層×repo群)、repo群 = home-assistant/core か否か
実行(humans_md/ で): uv run work/baseline/cr_rate_and_weights.py → work/baseline/cr_rate_and_weights.txt
"""
import collections, csv, glob, json, os, random, re, sys
import pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "work", "baseline"))
from extract import isbot, AGENT_TRAILER  # noqa: E402  (extract.py は import 時に再実行される)
out = []; P = lambda *a: out.append(" ".join(str(x) for x in a))

RAW = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/pilot_raw_full"))
P("== (a) pilot: repo 別 CR 使用率(人間作者・agent co-author なし PR、人間レビュアー、作者本人除く)")
tot = collections.Counter(); rows = []
for d in sorted(glob.glob(os.path.join(RAW, "*"))):
    repo = os.path.basename(d).replace("__", "/", 1); owner = repo.split("/")[0]
    meta = {}
    for l in open(os.path.join(d, "prs_full.jsonl")):
        try:
            j = json.loads(l)
        except json.JSONDecodeError:
            continue
        msgs = [c["commit"]["message"] or "" for c in ((j.get("commits") or {}).get("nodes") or [])]
        meta[j["number"]] = ((j.get("author") or {}).get("login"), any(AGENT_TRAILER.search(m) for m in msgs))
    c = collections.Counter(); npr = 0
    for l in open(os.path.join(d, "review_bodies.jsonl")):
        j = json.loads(l); m = meta.get(j["number"])
        if not m or isbot(m[0]) or m[1]:
            continue
        npr += 1
        for r in j["reviews"]:
            a = r.get("author")
            if isbot(a) or a == owner or a == m[0]:
                continue
            c[r["state"]] += 1
    n = sum(c.values()); tot += c
    rows.append((repo, npr, n, c["CHANGES_REQUESTED"], c["CHANGES_REQUESTED"] / n if n else 0))
for r in sorted(rows, key=lambda x: -x[2]):
    P(f"  {r[0]}: PR {r[1]} 人間レビュー {r[2]} CR {r[3]} 率 {r[4]:.3f}")
P(f" pilot 合計: 人間レビュー {sum(tot.values())} CR {tot['CHANGES_REQUESTED']} 率 {tot['CHANGES_REQUESTED'] / sum(tot.values()):.3f}  内訳 {dict(tot)}")
rr = sorted(r[4] for r in rows if r[2] >= 100)
P(f" repo 別率(人間レビュー>=100 の {len(rr)} repo)中央値 {rr[len(rr) // 2]:.3f} 最小 {rr[0]:.3f} 最大 {rr[-1]:.3f}")

rv = pd.read_parquet(f"{ROOT}/data/aidev/pr_reviews.parquet")
rv = rv[(rv["user_type"] == "User") & ~rv["user"].fillna("").map(isbot)]
P(f"\n== AIDev(全 agent PR)人間レビュー {len(rv)} CR {(rv.state == 'CHANGES_REQUESTED').sum()} 率 {(rv.state == 'CHANGES_REQUESTED').mean():.3f}  内訳 {rv.state.value_counts().to_dict()}")
pr = pd.read_parquet(f"{ROOT}/data/aidev/pull_request.parquet")
if "repo_id" in pr.columns:
    rv = rv.merge(pr[["id", "repo_id"]].rename(columns={"id": "pr_id"}), on="pr_id")
    g = rv.groupby("repo_id")["state"].agg(n="size", cr=lambda s: (s == "CHANGES_REQUESTED").mean())
    g = g[g.n >= 100]
    P(f" AIDev repo 別率(人間レビュー>=100 の {len(g)} repo)中央値 {g.cr.median():.3f} 最小 {g.cr.min():.3f} 最大 {g.cr.max():.3f}")

P("\n== (b) 感度分析: 層×(home-assistant/core か否か)で重み付け")
m = {r["sid"]: r for r in csv.DictReader(open(f"{ROOT}/outputs/ghhuman/irr/irr_merged.csv"))}
smp = {r["sid"]: r for r in json.load(open(f"{ROOT}/outputs/ghhuman/sample100.json"))}
gh = [json.loads(l) for l in open(f"{ROOT}/work/baseline/ghhuman_blocks.jsonl")]
cell = lambda st, repo: (st, repo == "home-assistant/core")
pop = collections.Counter(cell("closed" if r["outcome"] == "closed" else "not_closed", r["repo"]) for r in gh if not r["agent_coauthor"])
sc = {k: cell(v["stratum"], v["repo"]) for k, v in smp.items()}
scnt = collections.Counter(sc.values())
P(" 母集団セル", dict(pop), " サンプルセル", dict(scnt))
valid = [k for k in m if m[k]["majority"] not in ("BOT", "UNK", "NOAGREE")]
w = lambda k: pop[sc[k]] / scnt[sc[k]]
share = lambda ks: sum(w(k) for k in ks if m[k]["majority"].startswith("H")) / sum(w(k) for k in ks)
random.seed(0)
bs = sorted(share([random.choice(valid) for _ in valid]) for _ in range(2000))
P(f" H系(層×HA重み) {share(valid):.3f} (95%CI {bs[50]:.3f}-{bs[1950]:.3f})")
for c in sorted(scnt, key=str):
    ss = [k for k in valid if sc[k] == c]
    P(f"  cell {c}: n_valid {len(ss)} H {sum(m[k]['majority'].startswith('H') for k in ss)}")
nh = [k for k in valid if smp[k]["repo"] != "home-assistant/core"]
popn = collections.Counter(k for k in pop.elements() if not k[1]) if False else {k: v for k, v in pop.items() if not k[1]}
P(" (HA を除く母集団だけを対象にした層補正 H系)",
  "%.3f" % (sum(pop[sc[k]] / scnt[sc[k]] for k in nh if m[k]["majority"].startswith("H")) / sum(pop[sc[k]] / scnt[sc[k]] for k in nh)))
open(f"{ROOT}/work/baseline/cr_rate_and_weights.txt", "w").write("\n".join(out) + "\n"); print("\n".join(out))
