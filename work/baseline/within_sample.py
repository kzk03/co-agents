"""同一 repo 内比較のサンプルと盲検ダンプを作る。
群:
  AG = pilot、エージェント関与(strong、within_classify.py)PR への人間 CR。50件(home-assistant/core は 20件まで)
  HU = pilot、人間作者 PR(agent_coauthor なし)への人間 CR。AG と (repo, 結末層) で 1:1 マッチ
  AO = AIDev(エージェント作者 PR)の人間 CR のうち pilot と共通の 5 repo の全件(37件)
  HO = pilot 人間作者 PR への人間 CR。AO と (repo, 結末層) で 1:1 マッチ(repo 内に足りなければ層は問わない)
共通: 1 PR 1件、同一レビュアー3件まで、ghhuman sample100 に入った PR は除外、seed=7
ダンプ: 群・結末・作者種別を伏せ、4群をシャッフルして W001.. の通し番号を振る。形式は sample.py と同じ
実行(humans_md/ で): uv run work/baseline/within_sample.py
出力: work/baseline/within/{sample.json, dump.txt, sample_summary.txt}(キー: sid→群は sample.json にだけ持つ)
"""
import collections, json, os, random, subprocess
import pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
W = f"{ROOT}/work/baseline"; OUT = f"{W}/within"
rng = random.Random(7)
st = lambda o: "closed" if o == "closed" else "not_closed"
blocks = [json.loads(l) for l in open(f"{OUT}/blocks_agent.jsonl")]
used_pr = {(r["repo"], r["number"]) for r in json.load(open(f"{ROOT}/outputs/ghhuman/sample100.json"))}
used_rev = collections.Counter()


def ok(b):
    return (b["repo"], b["number"]) not in used_pr and used_rev[b["reviewer"]] < 3


def take(b, grp):
    used_pr.add((b["repo"], b["number"])); used_rev[b["reviewer"]] += 1
    return dict(grp=grp, src="pilot", **{k: b[k] for k in ("rid", "repo", "number", "reviewer", "submittedAt", "outcome", "agent_level", "body", "comments")})


strong = [b for b in blocks if b["agent_level"] == "strong"]; rng.shuffle(strong)
none_ = [b for b in blocks if b["agent_level"] == "none"]; rng.shuffle(none_)
AG = []
for b in strong:
    if len(AG) >= 50:
        break
    if b["repo"] == "home-assistant/core" and sum(a["repo"] == b["repo"] for a in AG) >= 20:
        continue
    if ok(b):
        AG.append(take(b, "AG"))
# 非 HA が足りなければ HA で埋める
for b in strong:
    if len(AG) >= 50:
        break
    if ok(b):
        AG.append(take(b, "AG"))


def match(targets, grp):
    res, miss = [], 0
    for t in targets:
        c = [b for b in none_ if b["repo"].lower() == t["repo"].lower() and st(b["outcome"]) == st(t["outcome"]) and ok(b)]
        if not c:
            c = [b for b in none_ if b["repo"].lower() == t["repo"].lower() and ok(b)]; miss += 1
        if c:
            res.append(take(c[0], grp))
    return res, miss


HU, miss_hu = match(AG, "HU")

cr = pd.read_parquet(f"{ROOT}/outputs/aidev/human_blocks.parquet")
cr["repo"] = cr["html_url"].str.split("github.com/").str[1].str.split("/pull/").str[0]
OV = {"dotnet/docs", "dotnet/runtime", "getsentry/sentry", "home-assistant/core", "ydb-platform/ydb"}
cr = cr[cr["repo"].str.lower().isin(OV)].sort_values("id")
rc = pd.read_parquet(f"{ROOT}/data/aidev/pr_review_comments.parquet")
rc = rc[rc["in_reply_to_id"].isna()].sort_values("id")
AO = []
for _, r in cr.iterrows():
    com = [dict(path=str(c["path"]), body=str(c["body"])) for _, c in rc[rc["pull_request_review_id"] == r["id"]].iterrows()
           if str(c["body"] or "").strip()]
    AO.append(dict(grp="AO", src="aidev", rid=str(r["id"]), repo=r["repo"], number=int(r["html_url"].split("/pull/")[1]),
                   reviewer=r["user"], submittedAt=str(r["submitted_at"]), outcome=r["outcome"], agent_level=r["agent"],
                   body=str(r["body"]).strip() if isinstance(r["body"], str) else "", comments=com, title=r["title"]))
HO, miss_ho = match(AO, "HO")

allr = AG + HU + AO + HO
cache_f = f"{W}/titles_cache.json"; cache = json.load(open(cache_f))
for r in allr:
    if "title" in r:
        continue
    key = f"{r['repo']}#{r['number']}"
    if key not in cache:
        cache[key] = subprocess.run(["gh", "api", f"repos/{r['repo']}/pulls/{r['number']}", "--jq", ".title"],
                                    capture_output=True, text=True).stdout.strip()
    r["title"] = cache[key]
json.dump(cache, open(cache_f, "w"), ensure_ascii=False, indent=1)
rng.shuffle(allr)
with open(f"{OUT}/dump.txt", "w") as f:
    for i, r in enumerate(allr):
        r["sid"] = f"W{i + 1:03d}"
        f.write(f"### {r['sid']} {r['repo']} | {r['title'][:90]}\n")
        body = r["body"].replace("\n", " ")
        f.write(f"  BODY: {body[:500] if body else 'nan'}\n")
        for c in r["comments"][:6]:
            f.write(f"  [{c['path'].split('/')[-1]}] " + c["body"].replace("\n", " ")[:350] + "\n")
json.dump(allr, open(f"{OUT}/sample.json", "w"), ensure_ascii=False, indent=1)
L = [f"miss(層が合わず repo だけでマッチ) HU {miss_hu} HO {miss_ho}"]
for g in ["AG", "HU", "AO", "HO"]:
    rs = [r for r in allr if r["grp"] == g]
    L.append(f"{g}: n={len(rs)} repo {dict(collections.Counter(r['repo'] for r in rs).most_common())} 結末 {dict(collections.Counter(st(r['outcome']) for r in rs))}")
open(f"{OUT}/sample_summary.txt", "w").write("\n".join(L) + "\n"); print("\n".join(L))
