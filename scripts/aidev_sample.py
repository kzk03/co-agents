"""AIDev-pop の人間 CHANGES_REQUESTED から100件を層化抽出し、分類用テキストを作る。

実行(humans_md/ で): uv run scripts/aidev_sample.py
- 層: PR の結末(closed=強い拒否 50件 / merged・open 50件)
- 同じ repo・同じレビュアーからはそれぞれ2件まで、seed=42
- 分類用ダンプには PR の結末を載せない(結末を知った状態での分類を避ける)
出力: outputs/aidev/sample100.json、outputs/aidev/dump.txt
"""
import json
import os

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
D = os.path.join(ROOT, "data", "aidev")
OUT = os.path.join(ROOT, "outputs", "aidev")

cr = pd.read_parquet(f"{OUT}/human_blocks.parquet")
rc = pd.read_parquet(f"{D}/pr_review_comments.parquet")
rc = rc[rc["in_reply_to_id"].isna()].sort_values("id")

cr["stratum"] = cr["outcome"].map(lambda o: "closed" if o == "closed" else "not_closed")
target = {"closed": 50, "not_closed": 50}
cr = cr.sample(frac=1, random_state=42)
pick, used_repo, used_rev, cnt = [], {}, {}, {k: 0 for k in target}
for _, r in cr.iterrows():
    k = r["stratum"]
    if cnt[k] >= target[k] or used_repo.get(r["repo_id"], 0) >= 2 or used_rev.get(r["user"], 0) >= 2:
        continue
    pick.append(r); cnt[k] += 1
    used_repo[r["repo_id"]] = used_repo.get(r["repo_id"], 0) + 1
    used_rev[r["user"]] = used_rev.get(r["user"], 0) + 1
s = pd.DataFrame(pick).reset_index(drop=True)
s["sid"] = [f"G{i + 1:03d}" for i in range(len(s))]

rows = []
with open(f"{OUT}/dump.txt", "w") as f:
    for _, r in s.iterrows():
        inl = rc[rc["pull_request_review_id"] == r["id"]]
        repo = r["html_url"].split("github.com/")[1].split("/pull/")[0]
        f.write(f"### {r['sid']} {repo} agent={r['agent']} | {str(r['title'])[:90]}\n")
        body = str(r["body"] or "").strip().replace("\n", " ")
        if body and body != "None":
            f.write(f"  BODY: {body[:500]}\n")
        for _, c in inl.head(6).iterrows():
            f.write(f"  [{str(c['path']).split('/')[-1]}] " + str(c["body"]).replace("\n", " ")[:350] + "\n")
        rows.append({"sid": r["sid"], "review_id": int(r["id"]), "pr_id": int(r["pr_id"]), "repo": repo,
                     "agent": r["agent"], "outcome": r["outcome"], "stratum": r["stratum"], "reviewer": r["user"],
                     "html_url": r["html_url"], "title": r["title"], "body": r["body"],
                     "inline": [{"path": c["path"], "body": c["body"], "diff_hunk": c["diff_hunk"]} for _, c in inl.iterrows()]})
json.dump(rows, open(f"{OUT}/sample100.json", "w"), ensure_ascii=False, indent=1)
print(len(s), cnt, s["agent"].value_counts().to_dict())
