"""v1 コードブックで sonnet に分類させる(12件/呼び出し、出力があればスキップ)。
uv run python work/codebook/run_sonnet.py"""
import json, os, subprocess
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
W = os.path.join(ROOT, "work/codebook"); OUT = os.path.join(W, "sonnet"); os.makedirs(OUT, exist_ok=True)
CWD = os.path.join(W, "_cwd"); os.makedirs(CWD, exist_ok=True)
DENY = "Bash,Read,Write,Edit,WebFetch,WebSearch,Agent,Glob,Grep,TodoWrite,ToolSearch,Skill,NotebookEdit"
tg = json.load(open(os.path.join(W, "targets.json")))
book = open(os.path.join(W, "prompt_v1.md")).read()
procs = []
for i in range(0, len(tg), 12):
    fn = os.path.join(OUT, f"batch{i//12}.jsonl")
    if os.path.exists(fn) and os.path.getsize(fn) > 0:
        continue
    items = "\n\n".join(t["text"] for t in tg[i:i+12])
    p = subprocess.Popen(["claude", "-p", "--model", "sonnet", "--max-turns", "1", "--disallowedTools", DENY],
                         stdin=subprocess.PIPE, stdout=open(fn, "w"), stderr=subprocess.DEVNULL, text=True, cwd=CWD)
    p.stdin.write(book + "\n\nITEMS:\n" + items); p.stdin.close(); procs.append(p)
for p in procs:
    p.wait()
print("calls", len(procs))
