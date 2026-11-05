"""Coder A: extract decision-authority units from each document and code them.

Usage: python3 code_units.py <model> <out_jsonl>
Calls `claude -p --model <model>` once per document with codebook.md + the document.
"""
import json, subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL, OUT = sys.argv[1], sys.argv[2]
MAXC = 60000
CODEBOOK = open(os.path.join(HERE, "codebook.md"), encoding="utf-8").read()


def docs():
    for x in json.load(open(os.path.join(HERE, "humans_selection.json"))):
        if x["decision"] == "include":
            yield {"doc_type": "HUMANS.md", "doc_id": x["repo"] + "/" + x["path"],
                   "file": os.path.join(HERE, "..", "github", "humans_files", x["file"])}
    for x in json.load(open(os.path.join(HERE, "agents_sample.json"))):
        if x.get("fetched"):
            yield {"doc_type": "AGENTS.md", "doc_id": x["repo"] + "/" + x["path"], "file": os.path.join(HERE, x["file"])}


PROMPT = """You are a careful qualitative coder. Follow the codebook exactly.

<codebook>
{cb}
</codebook>

Extract EVERY qualifying unit from the document below and code it. If there are none, return [].
Return ONLY a JSON array (no prose, no code fences) of objects with keys quote, stage, assignee, enforceable.

<document name="{name}">
{body}
</document>"""


def run(d):
    body = open(d["file"], encoding="utf-8", errors="ignore").read()
    trunc = len(body) > MAXC
    p = PROMPT.format(cb=CODEBOOK, name=d["doc_id"], body=body[:MAXC])
    for attempt in range(3):
        r = subprocess.run(["claude", "-p", "--model", MODEL], input=p, capture_output=True, text=True, cwd="/tmp")
        s = r.stdout.strip()
        s = s[s.find("["): s.rfind("]") + 1] if "[" in s else s
        try:
            units = json.loads(s)
            return {**d, "chars": len(body), "truncated": trunc, "units": units, "error": None}
        except Exception as e:
            err = f"{e}: {r.stdout[:200]} {r.stderr[:200]}"
    return {**d, "chars": len(body), "truncated": trunc, "units": [], "error": err}


if __name__ == "__main__":
    ds = list(docs())
    with ThreadPoolExecutor(8) as ex, open(OUT, "w", encoding="utf-8") as f:
        for res in ex.map(run, ds):
            f.write(json.dumps(res, ensure_ascii=False) + "\n"); f.flush()
    print(len(ds), "docs")
