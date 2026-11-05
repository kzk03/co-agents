"""Re-run coder A only for documents that failed in coderA_opus.jsonl (session limit), writing a new file.

Usage: python3 rerun_failed.py <model> <in_jsonl> <out_jsonl>
"""
import json, sys
from concurrent.futures import ThreadPoolExecutor
sys.argv = [sys.argv[0], sys.argv[1], "/dev/null"] + sys.argv[2:]
import code_units

MODEL, SRC, OUT = sys.argv[1], sys.argv[3], sys.argv[4]
code_units.MODEL = MODEL
failed = [{k: r[k] for k in ("doc_type", "doc_id", "file")} for r in map(json.loads, open(SRC, encoding="utf-8")) if r["error"]]
with ThreadPoolExecutor(4) as ex, open(OUT, "w", encoding="utf-8") as f:
    for res in ex.map(code_units.run, failed):
        f.write(json.dumps(res, ensure_ascii=False) + "\n"); f.flush()
print(len(failed), "docs re-run")
