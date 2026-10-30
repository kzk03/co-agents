"""文書化済みか(レビュー時点の README/CONTRIBUTING/AGENTS.md 等に理由が既に書かれていたか)を sonnet で判定。
対象: 私か sonnet のどちらかが K/R/D とした件。repo ごとに文書を1回だけ渡し、≤150k 字で詰める。
uv run python work/codebook/run_doccheck.py"""
import csv, json, os, subprocess
W = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(W, "doccheck"); os.makedirs(OUT, exist_ok=True)
CWD = os.path.join(W, "_cwd"); DENY = "Bash,Read,Write,Edit,WebFetch,WebSearch,Agent,Glob,Grep,TodoWrite,ToolSearch,Skill,NotebookEdit"
m = {r["sid"]: r for r in csv.DictReader(open(os.path.join(W, "coding_merged_v1.csv")))}
tg = {t["sid"]: t for t in json.load(open(os.path.join(W, "targets.json")))}
krd = lambda c: c[:1] in ("K", "R", "D")
items = [s for s in m if krd(m[s]["me"]) or krd(m[s]["sonnet"])]
byrepo = {}
for s in items:
    d = json.load(open(os.path.join(W, "cache", f"{s}.json")))
    if not d["docs"]:
        continue
    byrepo.setdefault(d["repo"], []).append((s, d))
INSTR = """For each review item below, decide whether the RULE, FACT or DECISION underlying the reviewer's primary reason was ALREADY WRITTEN in the repository documents provided for that repository (snapshot at the PR's base commit, before the review).
- yes: the documents state it explicitly enough that an author who read them would have avoided this objection
- partial: the documents state a related general rule/fact, but not specific enough to have prevented this objection
- no: not stated
Judge only from the provided documents. Quote the shortest supporting sentence (<=200 chars) for yes/partial, else "".
Output ONLY JSON lines, one per item, no prose: {"sid":"H004","written":"yes","quote":"..."}
"""
groups, cur, size = [], [], 0
for repo, lst in sorted(byrepo.items()):
    docs = lst[0][1]["docs"]
    block = f"=== REPOSITORY {repo} ===\n" + "\n".join(f"--- DOCUMENT {k} ---\n{v[:60000]}" for k, v in docs.items())
    block += "\n\n=== REVIEW ITEMS FOR " + repo + " ===\n" + "\n\n".join(tg[s]["text"] for s, _ in lst)
    if cur and size + len(block) > 150000:
        groups.append(cur); cur, size = [], 0
    cur.append(block); size += len(block)
if cur:
    groups.append(cur)
print("items", len(items), "with docs", sum(len(v) for v in byrepo.values()), "calls", len(groups))
procs = []
for i, g in enumerate(groups):
    fn = os.path.join(OUT, f"group{i}.jsonl")
    if os.path.exists(fn) and os.path.getsize(fn) > 0:
        continue
    p = subprocess.Popen(["claude", "-p", "--model", "sonnet", "--max-turns", "1", "--disallowedTools", DENY],
                         stdin=subprocess.PIPE, stdout=open(fn, "w"), stderr=subprocess.DEVNULL, text=True, cwd=CWD)
    p.stdin.write(INSTR + "\n\n" + "\n\n".join(g)); p.stdin.close(); procs.append(p)
for p in procs:
    p.wait()
print("ran", len(procs))
