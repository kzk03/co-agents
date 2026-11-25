"""SWE-chat の全リポジトリを data/repos/ に clone する(blobless・bare)。

履歴(コミットとツリー)だけを取り、ファイル本体は必要になったときに取る。
既にあるものは fetch で更新する。結果は data/repos/_status.csv に書く。
  --limit N  先頭 N 件だけ(試し用)
  --jobs N   並列数(既定 8)
"""
import argparse, csv, os, subprocess
from concurrent.futures import ThreadPoolExecutor
import duckdb

p = argparse.ArgumentParser()
p.add_argument("--limit", type=int)
p.add_argument("--jobs", type=int, default=8)
a = p.parse_args()

OUT = "data/repos"
os.makedirs(OUT, exist_ok=True)
rows = duckdb.sql("select repo_id, url from 'data/swe-chat/repositories.parquet' "
                  "order by num_sessions desc").fetchall()
if a.limit:
    rows = rows[: a.limit]
env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

def run(row):
    repo_id, url = row
    dest = os.path.join(OUT, url.removeprefix("https://github.com/").replace("/", "__") + ".git")
    if os.path.isdir(dest):
        cmd = ["git", "-C", dest, "fetch", "--quiet", "--prune", "origin", "+refs/heads/*:refs/heads/*"]
    else:
        cmd = ["git", "clone", "--quiet", "--bare", "--filter=blob:none", url, dest]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)
    status = "ok" if r.returncode == 0 else "error"
    print(status, url, flush=True)
    return repo_id, url, dest, status, r.stderr.strip().replace("\n", " ")[:300]

with ThreadPoolExecutor(a.jobs) as ex:
    res = list(ex.map(run, rows))
with open(os.path.join(OUT, "_status.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["repo_id", "url", "path", "status", "stderr"]); w.writerows(res)
print(f"done: {sum(r[3]=='ok' for r in res)}/{len(res)} ok")
