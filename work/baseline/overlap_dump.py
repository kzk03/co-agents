"""AIDev と pilot で共通の 5 repo について、AIDev 側の人間 CR を全件ダンプ(同 repo 比較用、Opus 単独で分類)。
実行(humans_md/ で): uv run work/baseline/overlap_dump.py → work/baseline/overlap_aidev_dump.txt
"""
import os
import pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OV = {"dotnet/docs", "dotnet/runtime", "getsentry/sentry", "home-assistant/core", "ydb-platform/ydb"}
cr = pd.read_parquet(f"{ROOT}/outputs/aidev/human_blocks.parquet")
cr["repo"] = cr["html_url"].str.split("github.com/").str[1].str.split("/pull/").str[0]
cr = cr[cr["repo"].str.lower().isin(OV)].sort_values("id").reset_index(drop=True)
rc = pd.read_parquet(f"{ROOT}/data/aidev/pr_review_comments.parquet")
rc = rc[rc["in_reply_to_id"].isna()].sort_values("id")
with open(f"{ROOT}/work/baseline/overlap_aidev_dump.txt", "w") as f:
    for i, r in cr.iterrows():
        f.write(f"### O{i + 1:03d} {r['repo']} agent={r['agent']} outcome={r['outcome']} id={r['id']} | {str(r['title'])[:90]}\n")
        body = str(r["body"] or "").strip().replace("\n", " ")
        f.write(f"  BODY: {body[:500]}\n")
        for _, c in rc[rc["pull_request_review_id"] == r["id"]].head(6).iterrows():
            f.write(f"  [{str(c['path']).split('/')[-1]}] " + str(c["body"]).replace("\n", " ")[:350] + "\n")
print(len(cr), cr["repo"].value_counts().to_dict(), cr["outcome"].value_counts().to_dict())
