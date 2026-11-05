"""Coder B: independently re-code the units extracted by coder A (stage, assignee, enforceable).

Usage: python3 recode_units.py <coderA.jsonl> <model> <out_jsonl>
Coder B sees only the codebook, the document name, and the quoted units (not coder A's codes).
"""
import json, subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
SRC, MODEL, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
CODEBOOK = open(os.path.join(HERE, "codebook.md"), encoding="utf-8").read()

PROMPT = """You are a careful qualitative coder. Follow the codebook exactly.

<codebook>
{cb}
</codebook>

The following units were extracted from the document "{name}". Code EACH unit independently with stage, assignee, enforceable.
Return ONLY a JSON array (no prose, no code fences) with one object per unit, in the same order, with keys i, stage, assignee, enforceable.

<units>
{units}
</units>"""


def run(r):
    if not r["units"]:
        return {**r, "codesB": [], "errorB": None}
    us = "\n".join(json.dumps({"i": i, "quote": u.get("quote", "")}, ensure_ascii=False) for i, u in enumerate(r["units"]))
    p = PROMPT.format(cb=CODEBOOK, name=r["doc_id"], units=us)
    err = None
    for attempt in range(3):
        o = subprocess.run(["claude", "-p", "--model", MODEL], input=p, capture_output=True, text=True, cwd="/tmp")
        s = o.stdout.strip()
        s = s[s.find("["): s.rfind("]") + 1] if "[" in s else s
        try:
            codes = json.loads(s)
            if len(codes) == len(r["units"]):
                return {**r, "codesB": codes, "errorB": None}
            err = f"length mismatch {len(codes)} vs {len(r['units'])}"
        except Exception as e:
            err = f"{e}: {o.stdout[:200]}"
    return {**r, "codesB": None, "errorB": err}


if __name__ == "__main__":
    rows = [json.loads(l) for l in open(SRC, encoding="utf-8")]
    with ThreadPoolExecutor(8) as ex, open(OUT, "w", encoding="utf-8") as f:
        for res in ex.map(run, rows):
            f.write(json.dumps(res, ensure_ascii=False) + "\n"); f.flush()
    print(len(rows), "docs")
