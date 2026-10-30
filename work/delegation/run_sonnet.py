"""Independent upstream judging with claude -p --model sonnet (blind to my labels, group, agent). Batches of 10, max 4 parallel.
Output: sonnet/{agent,human}_batchNN.jsonl. Human: only items with req_src=issue (others have no request -> U4 by rule)."""
import json, os, subprocess, sys
BASE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(BASE, "sonnet"); CWD = os.path.join(OUT, "_cwd")
os.makedirs(CWD, exist_ok=True)
DENY = "Bash,Read,Write,Edit,WebFetch,WebSearch,Agent,Glob,Grep,TodoWrite,ToolSearch,Skill,NotebookEdit"
book = open(os.path.join(BASE, "upstream_codebook.md")).read()
def fmt(r):
    return f"### {r['sid']} | src={r['req_src']}\nTITLE: {r['title']}\n--- REQUEST ---\n{(r['request'] or '(none)')[:3000]}\n--- REVIEW (CR) ---\n{r['review']}\n"
jobs = []
for side in ["agent", "human"]:
    rows = [json.loads(l) for l in open(os.path.join(BASE, f"material_{side}.jsonl"))]
    if side == "human": rows = [r for r in rows if r["req_src"] == "issue"]
    for b in range(0, len(rows), 10):
        jobs.append((os.path.join(OUT, f"{side}_batch{b//10:02d}.jsonl"), "\n".join(fmt(r) for r in rows[b:b+10])))
jobs = [j for j in jobs if not (os.path.exists(j[0]) and os.path.getsize(j[0]) > 0)]
print("calls:", len(jobs))
for i in range(0, len(jobs), 4):
    procs = []
    for fn, txt in jobs[i:i+4]:
        out = open(fn, "w")
        p = subprocess.Popen(["claude", "-p", "--model", "sonnet", "--max-turns", "1", "--disallowedTools", DENY],
                             stdin=subprocess.PIPE, stdout=out, stderr=subprocess.DEVNULL, text=True, cwd=CWD)
        p.stdin.write(book + "\n\nITEMS:\n" + txt); p.stdin.close(); procs.append(p)
    for p in procs: p.wait()
    print("done", i + len(procs), flush=True)
