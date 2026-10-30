"""gh api graphql で一括取得(呼び出しは work/explore/gh_calls.log に1行ずつ記録)。
A: repo ごとの AGENTS.md / CLAUDE.md / .github/copilot-instructions.md の既定ブランチ履歴(最古コミット日 = 追加日の近似)
B: AIDev の人間 CR がついた PR ごとの reviews(authorAssociation)と commits(committedDate)
uv run python work/explore/fetch_gh.py {repos|prs|pilot} [max_calls]"""
import json, os, subprocess, sys, datetime
import pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
E = os.path.join(ROOT, "work/explore"); C = os.path.join(E, "cache_gh"); os.makedirs(C, exist_ok=True)
LOG = os.path.join(E, "gh_calls.log")
FILES = {"ag": "AGENTS.md", "cl": "CLAUDE.md", "cp": ".github/copilot-instructions.md"}

def gql(q, tag):
    with open(LOG, "a") as f:
        f.write(f"{datetime.datetime.now().isoformat()} graphql {tag} 1\n")
    r = subprocess.run(["gh", "api", "graphql", "-f", f"query={q}"], capture_output=True, text=True)
    try:
        j = json.loads(r.stdout)
    except Exception:
        return {"data": None, "errors": [r.stderr[:300]]}
    return j

def esc(s):
    return s.replace('"', '\\"')

def repos_job(maxc, pilot=False):
    if pilot:
        P = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/pilot_raw_full"))
        repos = sorted(d.replace("__", "/", 1) for d in os.listdir(P) if "__" in d)
        return fetch_repos(repos, maxc, os.path.join(C, "repos_pilot.jsonl"))
    pr = pd.read_parquet(os.path.join(ROOT, "data/aidev/pull_request.parquet"))
    rv = pd.read_parquet(os.path.join(ROOT, "data/aidev/pr_reviews.parquet"))
    cr = rv[(rv.state == "CHANGES_REQUESTED") & (rv.user_type == "User")]
    n = pr.repo_url.value_counts()
    repos = sorted(set(pr[pr.id.isin(cr.pr_id)].repo_url) | set(n[n >= 20].index))
    repos = [u.split("/repos/")[1] for u in repos]
    return fetch_repos(repos, maxc, os.path.join(C, "repos.jsonl"))

def fetch_repos(repos, maxc, out):
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)["repo"] for l in open(out) if json.loads(l)["ok"]}
    todo = [r for r in repos if r not in done]
    print("repos", len(repos), "todo", len(todo))
    B = int(os.environ.get("B", 20)); calls = 0
    for i in range(0, len(todo), B):
        if calls >= maxc: break
        chunk = todo[i:i + B]; parts = []
        for k, r in enumerate(chunk):
            o, nm = r.split("/", 1)
            hs = " ".join(f'{a}: history(path:"{p}", first:100){{totalCount nodes{{committedDate}}}}' for a, p in FILES.items())
            ex = " ".join(f'x{a}: object(expression:"HEAD:{p}"){{id}}' for a, p in FILES.items())
            parts.append(f'r{k}: repository(owner:"{esc(o)}", name:"{esc(nm)}"){{ nameWithOwner {ex} defaultBranchRef{{ name target{{ ... on Commit {{ {hs} }} }} }} }}')
        j = gql("query { " + " ".join(parts) + " rateLimit{cost remaining} }", "repos"); calls += 1
        d = j.get("data") or {}
        with open(out, "a") as f:
            for k, r in enumerate(chunk):
                x = d.get(f"r{k}")
                rec = {"repo": r, "ok": x is not None}
                if x:
                    rec["branch"] = (x.get("defaultBranchRef") or {}).get("name")
                    t = ((x.get("defaultBranchRef") or {}).get("target") or {})
                    for a in FILES:
                        h = t.get(a) or {"totalCount": 0, "nodes": []}
                        ds = [nd["committedDate"] for nd in h["nodes"]]
                        rec[a] = {"n": h["totalCount"], "first": min(ds) if ds else None, "complete": h["totalCount"] <= 100,
                                  "exists_now": x.get(f"x{a}") is not None}
                f.write(json.dumps(rec) + "\n")
        print(i, "rate", (d.get("rateLimit") or {}), "errors", len(j.get("errors") or []))

def prs_job(maxc):
    pr = pd.read_parquet(os.path.join(ROOT, "data/aidev/pull_request.parquet"))
    rv = pd.read_parquet(os.path.join(ROOT, "data/aidev/pr_reviews.parquet"))
    cr = rv[(rv.state == "CHANGES_REQUESTED") & (rv.user_type == "User")]
    t = pr[pr.id.isin(cr.pr_id)][["id", "number", "repo_url"]]
    out = os.path.join(C, "prs.jsonl")
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)["pr_id"] for l in open(out) if json.loads(l)["ok"]}
    todo = [r for r in t.itertuples() if int(r.id) not in done]
    print("prs", len(t), "todo", len(todo))
    B = int(os.environ.get("B", 40)); calls = 0
    for i in range(0, len(todo), B):
        if calls >= maxc: break
        chunk = todo[i:i + B]; parts = []
        for k, r in enumerate(chunk):
            o, nm = r.repo_url.split("/repos/")[1].split("/", 1)
            parts.append(f'p{k}: repository(owner:"{esc(o)}", name:"{esc(nm)}"){{ pullRequest(number:{int(r.number)}){{ merged state '
                         f'reviews(first:40){{nodes{{author{{login}} authorAssociation state submittedAt}}}} '
                         f'commits(first:100){{totalCount nodes{{commit{{committedDate authoredDate}}}}}} }} }}')
        j = gql("query { " + " ".join(parts) + " rateLimit{cost remaining} }", "prs"); calls += 1
        d = j.get("data") or {}
        with open(out, "a") as f:
            for k, r in enumerate(chunk):
                x = (d.get(f"p{k}") or {}).get("pullRequest")
                rec = {"pr_id": int(r.id), "ok": x is not None}
                if x:
                    rec["reviews"] = [dict(login=(n["author"] or {}).get("login"), assoc=n["authorAssociation"], state=n["state"], at=n["submittedAt"]) for n in x["reviews"]["nodes"]]
                    rec["n_commits"] = x["commits"]["totalCount"]
                    rec["commits"] = [n["commit"]["committedDate"] for n in x["commits"]["nodes"]]
                f.write(json.dumps(rec) + "\n")
        print(i, "rate", (d.get("rateLimit") or {}), "errors", len(j.get("errors") or []))

if __name__ == "__main__":
    job = sys.argv[1]; maxc = int(sys.argv[2]) if len(sys.argv) > 2 else 999
    {"repos": repos_job, "prs": prs_job, "pilot": lambda m: repos_job(m, True)}[job](maxc)
