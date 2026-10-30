"""Fetch PR / timeline / linked issues (+issue timeline) for outputs/ghhuman/sample100.json via gh api, cached in cache/ (same scheme as fetch.py)."""
import json, os, re, sys
from fetch import gh, ISSUE_RE, ISSUE_URL_RE, ROOT

def linked_issues(repo, pr, tl):
    body = (pr.get("body") or "") if isinstance(pr, dict) else ""
    out = []
    for mm in ISSUE_RE.finditer(body): out.append((mm.group(1) or repo, mm.group(2)))
    for mm in ISSUE_URL_RE.finditer(body): out.append((mm.group(1), mm.group(2)))
    if isinstance(tl, list):
        for ev in tl:
            if ev.get("event") == "cross-referenced":
                src = (ev.get("source") or {}).get("issue") or {}
                if src and "pull_request" not in src:
                    mm = ISSUE_URL_RE.search(src.get("html_url", "") or "")
                    if mm: out.append((mm.group(1), mm.group(2)))
    return list(dict.fromkeys(out))

def main():
    s = json.load(open(os.path.join(ROOT, "outputs/ghhuman/sample100.json")))
    for x in s:
        repo, n = x["repo"], str(x["number"])
        pr = gh(f"repos/{repo}/pulls/{n}")
        tl = gh(f"repos/{repo}/issues/{n}/timeline?per_page=100", paginate=True)
        iss = linked_issues(repo, pr, tl)
        for r_, i in iss[:3]:
            gh(f"repos/{r_}/issues/{i}")
            gh(f"repos/{r_}/issues/{i}/timeline?per_page=100", paginate=True)
        print(x["sid"], repo, n, len(iss), "ERR" if isinstance(pr, dict) and "_error" in pr else "", flush=True)

if __name__ == "__main__":
    main()
