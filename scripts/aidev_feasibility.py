"""AIDev-pop で「人間がエージェント PR を止めた記録」がどれだけあるかを数える(実現可能性の確認)。

実行(humans_md/ で): uv run scripts/aidev_feasibility.py
入力: data/aidev/*.parquet(HF hao-li/AIDev の AIDev-pop テーブル)
出力: outputs/aidev/feasibility.txt、outputs/aidev/human_blocks.parquet(人間の CHANGES_REQUESTED 一覧)
"""
import os
import re

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
D = os.path.join(ROOT, "data", "aidev")
OUT = os.path.join(ROOT, "outputs", "aidev")
os.makedirs(OUT, exist_ok=True)
BOT = re.compile(r"(\[bot\]|bot$|-bot\b|copilot|coderabbit|sourcery|gemini-code-assist|codex|devin|cursor|claude|jules)", re.I)

lines = []
def say(*a):
    s = " ".join(str(x) for x in a); print(s); lines.append(s)

pr = pd.read_parquet(f"{D}/pull_request.parquet")
rv = pd.read_parquet(f"{D}/pr_reviews.parquet")
rc = pd.read_parquet(f"{D}/pr_review_comments.parquet")
cm = pd.read_parquet(f"{D}/pr_comments.parquet")

pr["outcome"] = pr.apply(lambda r: "merged" if pd.notna(r["merged_at"]) else ("closed" if r["state"] == "closed" else "open"), axis=1)
say("== PR")
say("PRs", len(pr), "repos", pr["repo_id"].nunique())
say(pr.groupby("agent")["outcome"].value_counts().unstack(fill_value=0).to_string())

say("\n== reviews")
say(rv.groupby(["user_type", "state"]).size().unstack(fill_value=0).to_string())

rv = rv.merge(pr[["id", "agent", "user", "outcome", "repo_id", "html_url", "title"]].rename(columns={"id": "pr_id", "user": "pr_user"}), on="pr_id", how="left")
rv["is_human"] = (rv["user_type"] == "User") & ~rv["user"].fillna("").str.contains(BOT.pattern.replace("(", "(?:", 1), regex=True) & (rv["user"] != rv["pr_user"])
n_inline = rc.groupby("pull_request_review_id").size()
rv["n_inline"] = rv["id"].map(n_inline).fillna(0).astype(int)
rv["has_body"] = rv["body"].fillna("").str.strip().str.len() > 0
rv["has_text"] = rv["has_body"] | (rv["n_inline"] > 0)

cr = rv[(rv["state"] == "CHANGES_REQUESTED") & rv["is_human"]].copy()
say("\n== 人間の CHANGES_REQUESTED(PR 作者本人・ボットを除く)")
say("reviews", len(cr), "PRs", cr["pr_id"].nunique(), "repos", cr["repo_id"].nunique(), "reviewers", cr["user"].nunique())
say("理由テキストあり(本文 or インライン)", int(cr["has_text"].sum()), f"({cr['has_text'].mean():.0%})",
    "本文あり", int(cr["has_body"].sum()), "インラインあり", int((cr["n_inline"] > 0).sum()))
say("PR の結末:", cr.drop_duplicates("pr_id")["outcome"].value_counts().to_dict())
say("エージェント別 PR 数:", cr.drop_duplicates("pr_id")["agent"].value_counts().to_dict())
strong = cr[cr["outcome"] == "closed"]
say("強い拒否(CR → マージされず閉じた) PRs", strong["pr_id"].nunique(), "うちテキストあり", strong[strong["has_text"]]["pr_id"].nunique())
top = cr["repo_id"].value_counts()
say("repo 集中: 上位10 repo が", f"{top.head(10).sum() / len(cr):.0%}", "の CR を占める")

say("\n== CR なしで閉じられた PR(コメントで止めた可能性)")
closed = pr[pr["outcome"] == "closed"]
hc = cm.merge(pr[["id", "user"]].rename(columns={"id": "pr_id", "user": "pr_user"}), on="pr_id")
hc = hc[(hc["user_type"] == "User") & ~hc["user"].fillna("").str.contains(BOT.pattern.replace("(", "(?:", 1), regex=True) & (hc["user"] != hc["pr_user"])]
no_cr_closed = closed[~closed["id"].isin(cr["pr_id"])]
say("closed PRs", len(closed), "うち人間 CR なし", len(no_cr_closed),
    "うち他者の人間コメントあり", int(no_cr_closed["id"].isin(hc["pr_id"]).sum()))

say("\n== 比較用: 人間が作った PR(agent=Human)")
hum = cr[cr["agent"] == "Human"]
say("Human PR に対する人間 CR", len(hum), "PRs", hum["pr_id"].nunique())

cr.to_parquet(f"{OUT}/human_blocks.parquet")
open(f"{OUT}/feasibility.txt", "w").write("\n".join(lines) + "\n")
