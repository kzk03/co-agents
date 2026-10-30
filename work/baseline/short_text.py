"""理由の乏しい CR の代理指標(母集団全件): インラインなし かつ body が 40 字未満。
実行(humans_md/ で): uv run work/baseline/short_text.py → work/baseline/short_text.txt
"""
import json, os
import pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
cr = pd.read_parquet(f"{ROOT}/outputs/aidev/human_blocks.parquet")
cr["short"] = (cr["n_inline"] == 0) & (cr["body"].fillna("").str.strip().str.len() < 40)
gh = pd.DataFrame([json.loads(l) for l in open(f"{ROOT}/work/baseline/ghhuman_blocks.jsonl")])
gh["short"] = (gh["comments"].map(len) == 0) & (gh["body"].str.strip().str.len() < 40)
out = []
for nm, d in [("aidev", cr), ("ghhuman(main)", gh[~gh["agent_coauthor"]]), ("ghhuman(agent co-author)", gh[gh["agent_coauthor"]])]:
    d = d.assign(st=d["outcome"].map(lambda o: "closed" if o == "closed" else "not_closed"))
    out.append(f"{nm}: short {d['short'].mean():.3f} (n={len(d)}) closed {d[d.st == 'closed']['short'].mean():.3f} not_closed {d[d.st == 'not_closed']['short'].mean():.3f}")
open(f"{ROOT}/work/baseline/short_text.txt", "w").write("\n".join(out) + "\n"); print("\n".join(out))
