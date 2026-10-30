"""判定者(Opus)用の表示。群ラベル・判定ファイルは出さない。
uv run python work/reproduce/show.py G004 A,B [aidev|gh]"""
import json, os, sys
sys.argv += [""] * 3
os.environ["REPRO_SET"] = sys.argv[3] or "aidev"
sys.path.insert(0, os.path.dirname(__file__))
import run  # noqa

sid, conds = sys.argv[1], sys.argv[2].split(",")
rec = json.load(open(os.path.join(run.DATA, f"{sid}.json")))
print(f"### {sid} {rec['repo']}#{rec['number']} — {rec['title']}\n--- HUMAN ---\n{run.human_text_any(sid)}\n")
for c in conds:
    print(f"--- LLM {c} ---\n{json.load(open(os.path.join(run.RES, f'{sid}_{c}.json')))['text']}\n")
