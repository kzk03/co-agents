"""Fetch PR / timeline / linked issues for sample100 via gh api, cached in cache/."""
import json, os, re, subprocess, sys, time
import pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "cache")
ROOT = os.path.abspath(os.path.join(BASE, "../.."))

def gh(path, paginate=False):
    fn = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]+", "_", path) + ".json")
    if os.path.exists(fn):
        return json.load(open(fn))
    cmd = ["gh", "api", "-H", "Accept: application/vnd.github+json", path]
    if paginate:
        cmd.insert(2, "--paginate"); cmd.insert(3, "--slurp")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        data = {"_error": r.stderr.strip()[:300]}
    else:
        data = json.loads(r.stdout)
        if paginate:
            data = [x for page in data for x in page]
    json.dump(data, open(fn, "w"))
    time.sleep(0.2)
    return data

ISSUE_RE = re.compile(r"(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s*:?\s+(?:([\w.-]+/[\w.-]+))?#(\d+)", re.I)
ISSUE_URL_RE = re.compile(r"github\.com/([\w.-]+/[\w.-]+)/issues/(\d+)")

def main():
    s = json.load(open(os.path.join(ROOT, "outputs/aidev/sample100.json")))
    for x in s:
        m = re.match(r"https://github.com/([^/]+/[^/]+)/pull/(\d+)", x["html_url"])
        repo, n = m.group(1), m.group(2)
        pr = gh(f"repos/{repo}/pulls/{n}")
        tl = gh(f"repos/{repo}/issues/{n}/timeline?per_page=100", paginate=True)
        body = (pr.get("body") or "") if isinstance(pr, dict) else ""
        issues = set()
        for mm in ISSUE_RE.finditer(body):
            issues.add((mm.group(1) or repo, mm.group(2)))
        for mm in ISSUE_URL_RE.finditer(body):
            issues.add((mm.group(1), mm.group(2)))
        if isinstance(tl, list):
            for ev in tl:
                if ev.get("event") == "cross-referenced":
                    src = (ev.get("source") or {}).get("issue") or {}
                    if src and "pull_request" not in src:
                        u = src.get("html_url", "")
                        mm = ISSUE_URL_RE.search(u)
                        if mm: issues.add((mm.group(1), mm.group(2)))
        for r_, i in sorted(issues)[:3]:
            gh(f"repos/{r_}/issues/{i}")
            gh(f"repos/{r_}/issues/{i}/timeline?per_page=100", paginate=True)
        print(x["sid"], repo, n, len(issues), flush=True)

if __name__ == "__main__":
    main()
