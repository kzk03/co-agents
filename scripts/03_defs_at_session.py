"""各セッションの開始時点で、リポジトリに定義ファイルがあったかを判定する。

セッションの branch が clone にあればそれを、無ければ既定ブランチ(HEAD)を使い、
開始時刻より前の最新コミットのツリーから定義ファイルのパスを列挙する。
出力: data/derived/session_defs.parquet
"""
import os, re, subprocess
from concurrent.futures import ThreadPoolExecutor
import duckdb, pandas as pd

DEF = re.compile(r"(^|/)(CLAUDE\.md|AGENTS\.md|GEMINI\.md|\.cursorrules|\.windsurfrules|"
                 r"copilot-instructions\.md)$|(^|/)\.cursor/rules/[^/]+\.mdc?$", re.I)
status = pd.read_csv("data/repos/_status.csv")
ok = status[status.status == "ok"].set_index("repo_id").path.to_dict()
ses = duckdb.sql("""select session_id, repo_id, branch, agent,
       coalesce(try_cast(session_started_at as timestamptz), created_at) as t
       from 'data/swe-chat/sessions.parquet'""").df()

def git(path, *args):
    r = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None

def per_repo(item):
    repo_id, g = item
    path = ok.get(repo_id)
    out = []
    if path is None:
        return [dict(session_id=s, cloned=False) for s in g.session_id]
    heads = set((git(path, "for-each-ref", "--format=%(refname:short)", "refs/heads") or "").split())
    tree_cache = {}
    for row in g.itertuples():
        ref = row.branch if row.branch in heads else "HEAD"
        before = pd.Timestamp(row.t).isoformat() if pd.notna(row.t) else None
        commit = git(path, "rev-list", "-1", f"--before={before}", ref) if before else None
        files = []
        if commit:
            if commit not in tree_cache:
                ls = git(path, "ls-tree", "-r", "--name-only", commit) or ""
                tree_cache[commit] = [f for f in ls.splitlines() if DEF.search(f)]
            files = tree_cache[commit]
        out.append(dict(session_id=row.session_id, cloned=True, ref_used=ref,
                        commit=commit, def_files="|".join(files), n_def=len(files),
                        has_claude=any(f.lower().endswith("claude.md") for f in files),
                        has_agents=any(f.lower().endswith("agents.md") for f in files)))
    return out

with ThreadPoolExecutor(16) as ex:
    rows = [r for part in ex.map(per_repo, ses.groupby("repo_id")) for r in part]
df = ses.merge(pd.DataFrame(rows), on="session_id")
os.makedirs("data/derived", exist_ok=True)
df.to_parquet("data/derived/session_defs.parquet", index=False)
c = df[df.cloned]
print("sessions:", len(df), " cloned:", len(c), " commit found:", c.commit.notna().sum())
print("has any def file:", (c.n_def > 0).sum(), " CLAUDE.md:", c.has_claude.sum(), " AGENTS.md:", c.has_agents.sum())
