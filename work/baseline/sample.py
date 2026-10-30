"""ghhuman(人間作者 PR への人間 CHANGES_REQUESTED)から100件を層化抽出し、分類用ダンプを作る。

実行(humans_md/ で): uv run work/baseline/sample.py
- 母集団: ghhuman_blocks.jsonl のうち agent_coauthor=False
- 層: closed 50 / merged・open 50、seed=42、同一レビュアー2件まで
- 同一 repo 2件まで(AIDev と同じ)。ただし closed 層は 22 repo しかなく 2件上限では 50 件に届かないため、
  埋まらない場合だけ repo 上限を 3,4,... と1ずつ緩めて追加で走査する(緩めた上限は summary に出す)
- タイトルは pilot に無いので gh api で取得(titles_cache.json にキャッシュ)
- ダンプに PR の結末は載せない
出力: outputs/ghhuman/sample100.json, outputs/ghhuman/dump.txt
"""
import collections, json, os, random, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
W = os.path.join(ROOT, "work", "baseline")
OUT = os.path.join(ROOT, "outputs", "ghhuman"); os.makedirs(os.path.join(OUT, "irr"), exist_ok=True)

rows = [r for r in (json.loads(l) for l in open(os.path.join(W, "ghhuman_blocks.jsonl"))) if not r["agent_coauthor"]]
for r in rows:
    r["stratum"] = "closed" if r["outcome"] == "closed" else "not_closed"
random.Random(42).shuffle(rows)
target = {"closed": 50, "not_closed": 50}
pick, used_repo, used_rev, cnt = [], collections.Counter(), collections.Counter(), collections.Counter()
taken = set()
cap = 2
while any(cnt[k] < target[k] for k in target):
    for i, r in enumerate(rows):
        k = r["stratum"]
        if i in taken or cnt[k] >= target[k] or used_repo[r["repo"]] >= cap or used_rev[r["reviewer"]] >= 2:
            continue
        pick.append(r); taken.add(i); cnt[k] += 1; used_repo[r["repo"]] += 1; used_rev[r["reviewer"]] += 1
    if any(cnt[k] < target[k] for k in target):
        print(f"repo cap {cap}: {dict(cnt)} -> relax"); cap += 1
print("final repo cap", cap, dict(cnt))

cache_f = os.path.join(W, "titles_cache.json")
cache = json.load(open(cache_f)) if os.path.exists(cache_f) else {}
for r in pick:
    key = f"{r['repo']}#{r['number']}"
    if key not in cache:
        t = subprocess.run(["gh", "api", f"repos/{r['repo']}/pulls/{r['number']}", "--jq", ".title"],
                           capture_output=True, text=True).stdout.strip()
        cache[key] = t
json.dump(cache, open(cache_f, "w"), ensure_ascii=False, indent=1)

out = []
with open(os.path.join(OUT, "dump.txt"), "w") as f:
    for i, r in enumerate(pick):
        sid = f"H{i + 1:03d}"; title = cache[f"{r['repo']}#{r['number']}"]
        f.write(f"### {sid} {r['repo']} author=human | {title[:90]}\n")
        body = r["body"].replace("\n", " ")
        f.write(f"  BODY: {body[:500] if body else 'nan'}\n")
        for c in r["comments"][:6]:
            f.write(f"  [{c['path'].split('/')[-1]}] " + c["body"].replace("\n", " ")[:350] + "\n")
        out.append(dict(sid=sid, title=title, html_url=f"https://github.com/{r['repo']}/pull/{r['number']}", **r))
json.dump(out, open(os.path.join(OUT, "sample100.json"), "w"), ensure_ascii=False, indent=1)
print(len(out), "repos", len({r['repo'] for r in out}), "reviewers", len({r['reviewer'] for r in out}),
      "outcome", dict(collections.Counter(r['outcome'] for r in out)),
      "repo top", collections.Counter(r['repo'] for r in out).most_common(8))
