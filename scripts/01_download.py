"""SWE-chat を data/swe-chat/ に取得する。

既定では小さいテーブル(合計 約 0.15GB)だけを取る。
--conversations を付けると conversations.parquet(約 6.4GB)も取る。
gated データセットなので HF_TOKEN が必要。
"""
import argparse
from huggingface_hub import hf_hub_download

REPO = "SALT-NLP/SWE-chat"
SMALL = [
    "README.md", "sessions.parquet", "repositories.parquet",
    "session_logs.parquet", "checkpoints.parquet", "context_events.parquet",
    "skill_definitions.parquet", "skill_invocations.parquet",
    "subagent_tasks.parquet",
]

p = argparse.ArgumentParser()
p.add_argument("--conversations", action="store_true")
p.add_argument("--revision", default="202b071f18e03c79df5a7287565ce2ebc5ee7756")
a = p.parse_args()

files = SMALL + (["conversations.parquet"] if a.conversations else [])
for f in files:
    path = hf_hub_download(REPO, f, repo_type="dataset", revision=a.revision,
                           local_dir="data/swe-chat")
    print("ok", path)
