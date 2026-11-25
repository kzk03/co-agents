"""各セッション時点のコミットにある Claude Code の権限設定(.claude/settings.json)を取り出す。

リポジトリに commit された設定だけが見える。~/.claude/settings.json(ユーザー全体)と
.claude/settings.local.json(通常 gitignore)は見えない点に注意。
出力: data/derived/session_settings.parquet
"""
import json, os, subprocess
from concurrent.futures import ThreadPoolExecutor
import duckdb, pandas as pd

status = pd.read_csv("data/repos/_status.csv").set_index("repo_id").path.to_dict()
d = duckdb.sql("""select session_id, repo_id, commit from 'data/derived/session_defs.parquet'
                  where cloned and commit is not null""").df()
env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

def one(key):
    repo_id, commit = key
    path = status[repo_id]
    r = subprocess.run(["git", "-C", path, "show", f"{commit}:.claude/settings.json"],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        return repo_id, commit, False, None, None, None
    try:
        perm = json.loads(r.stdout).get("permissions", {}) or {}
    except Exception:
        return repo_id, commit, True, None, None, "parse_error"
    return (repo_id, commit, True, json.dumps(perm.get("allow", [])), json.dumps(perm.get("deny", [])),
            perm.get("defaultMode"))

keys = list(d[["repo_id", "commit"]].drop_duplicates().itertuples(index=False, name=None))
with ThreadPoolExecutor(16) as ex:
    rows = list(ex.map(one, keys))
s = pd.DataFrame(rows, columns=["repo_id", "commit", "has_settings", "allow", "deny", "default_mode"])
out = d.merge(s, on=["repo_id", "commit"], how="left")
out.to_parquet("data/derived/session_settings.parquet", index=False)
print("sessions:", len(out), " with .claude/settings.json:", int(out.has_settings.sum()),
      " with non-empty allow:", int((out.allow.fillna("[]") != "[]").sum()))
print(out.default_mode.value_counts(dropna=False).head())
