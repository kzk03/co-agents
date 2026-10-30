"""Per-PR material (request text + sampled CR text) for upstream judging.
Agent: outputs/aidev/sample100.json (all 100). Human: outputs/ghhuman/sample100.json (H all + same number of C, seed 0).
Request text = linked issue (created before PR) title/body + issue comments before PR creation;
  else Copilot 'Original prompt' section in PR body; else (agent only) PR body as proxy (agent-written).
Output: material_agent.jsonl, material_human.jsonl, judge_dump_{agent,human}.txt"""
import json, os, re, ast, random
import pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(BASE, "../.."))
CACHE = os.path.join(BASE, "cache")
REQ_MAX, REV_MAX = 3000, 2000
def load(path):
    fn = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]+", "_", path) + ".json")
    if not os.path.exists(fn): return None
    d = json.load(open(fn))
    return None if isinstance(d, dict) and "_error" in d else d
ISSUE_RE = re.compile(r"(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s*:?\s+(?:([\w.-]+/[\w.-]+))?#(\d+)", re.I)
ISSUE_URL_RE = re.compile(r"github\.com/([\w.-]+/[\w.-]+)/issues/(\d+)")
def section(body, key):
    m = re.search(key + r".*?\n(.*?)(</details>|\Z)", body, re.S | re.I)
    return m.group(1).strip() if m else None
def parse_list(v):
    if isinstance(v, list): return v
    try: return ast.literal_eval(v) if isinstance(v, str) and v.startswith("[") else []
    except Exception: return []

def request_for(repo, n, allow_proxy):
    pr = load(f"repos/{repo}/pulls/{n}"); tl = load(f"repos/{repo}/issues/{n}/timeline?per_page=100") or []
    if pr is None: return dict(req_src="pr_unavailable", request="", issue=None, issue_author=None, issue_n_precomments=0)
    body = pr.get("body") or ""
    cands = []
    for mm in ISSUE_RE.finditer(body): cands.append((mm.group(1) or repo, mm.group(2)))
    for mm in ISSUE_URL_RE.finditer(body): cands.append((mm.group(1), mm.group(2)))
    for ev in tl:
        if ev.get("event") == "cross-referenced":
            src = (ev.get("source") or {}).get("issue") or {}
            mm = ISSUE_URL_RE.search(src.get("html_url", "") or "")
            if mm and "pull_request" not in src: cands.append((mm.group(1), mm.group(2)))
    best = None
    for r_, i in list(dict.fromkeys(cands))[:3]:
        iss = load(f"repos/{r_}/issues/{i}"); itl = load(f"repos/{r_}/issues/{i}/timeline?per_page=100") or []
        if not iss or "pull_request" in iss or iss.get("created_at", "9") > pr["created_at"]: continue
        score = 2 if any(e.get("event") == "assigned" and (e.get("assignee") or {}).get("login") == "Copilot" for e in itl) else 1
        score += 0.5 if (r_, i) in cands[:1] else 0
        if best is None or score > best[0]: best = (score, r_, i, iss, itl)
    if best:
        _, r_, i, iss, itl = best
        coms = [e for e in itl if e.get("event") == "commented" and e.get("created_at", "9") < pr["created_at"]]
        txt = f"[ISSUE {r_}#{i} by {iss['user']['login']}] {iss.get('title') or ''}\n{iss.get('body') or ''}"
        for c in coms:
            txt += f"\n[ISSUE COMMENT by {(c.get('actor') or c.get('user') or {}).get('login')}] {c.get('body') or ''}"
        return dict(req_src="issue", request=txt, issue=f"{r_}#{i}", issue_author=iss["user"]["login"], issue_n_precomments=len(coms))
    for key in ["Original prompt", "Original issue description", "Original description"]:
        t = section(body, key)
        if t: return dict(req_src="pr_body:" + key, request=t, issue=None, issue_author=None, issue_n_precomments=0)
    if allow_proxy and body.strip():
        return dict(req_src="pr_body_proxy", request=body, issue=None, issue_author=None, issue_n_precomments=0)
    return dict(req_src="none", request="", issue=None, issue_author=None, issue_n_precomments=0)

def review_text(body, inl):
    b = "" if body in (None, "nan") else str(body)
    out = "BODY: " + (b if b else "(empty)")
    for c in inl[:8]:
        out += f"\n[{c.get('path')}] {c.get('body')}"
    return out[:REV_MAX]

def grp(cat):
    if not isinstance(cat, str): return "other"
    return "H" if cat.startswith("H") else ("C" if cat in ("C1", "C2", "C3", "M") else "other")

def main():
    # agent
    s = json.load(open(os.path.join(ROOT, "outputs/aidev/sample100.json")))
    irr = pd.read_csv(os.path.join(ROOT, "outputs/aidev/irr/irr_merged.csv")).set_index("sid")
    tab = pd.read_csv(os.path.join(BASE, "delegation_table.csv")).set_index("sid")
    A = []
    for x in s:
        m = re.match(r"https://github.com/([^/]+/[^/]+)/pull/(\d+)", x["html_url"]); repo, n = m.group(1), m.group(2)
        r = request_for(repo, n, allow_proxy=True)
        A.append(dict(sid=x["sid"], side="agent", agent=x["agent"], repo=repo, number=int(n), outcome=x["outcome"],
                      reviewer=x["reviewer"], majority=irr.loc[x["sid"], "majority"], group=grp(irr.loc[x["sid"], "majority"]),
                      reviewer_is_requester=tab.loc[x["sid"], "reviewer_is_requester"], title=x["title"],
                      review=review_text(x.get("body"), parse_list(x.get("inline"))), **r))
    # human
    s = json.load(open(os.path.join(ROOT, "outputs/ghhuman/sample100.json")))
    irr = pd.read_csv(os.path.join(ROOT, "outputs/ghhuman/irr/irr_merged.csv")).set_index("sid")
    H = [x for x in s if grp(irr.loc[x["sid"], "majority"]) == "H"]
    C = [x for x in s if grp(irr.loc[x["sid"], "majority"]) == "C"]
    random.seed(0); Csel = random.sample(C, len(H))
    sel = {x["sid"] for x in H + Csel}
    Hm = []
    for x in s:
        if x["sid"] not in sel: continue
        r = request_for(x["repo"], str(x["number"]), allow_proxy=False)
        Hm.append(dict(sid=x["sid"], side="human", agent="human", repo=x["repo"], number=int(x["number"]), outcome=x["outcome"],
                       reviewer=x["reviewer"], pr_author=x["pr_author"], majority=irr.loc[x["sid"], "majority"],
                       group=grp(irr.loc[x["sid"], "majority"]), title=x["title"],
                       review=review_text(x.get("body"), parse_list(x.get("comments"))), **r))
    for name, rows in [("agent", A), ("human", Hm)]:
        with open(os.path.join(BASE, f"material_{name}.jsonl"), "w") as f:
            for r in rows: f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
        with open(os.path.join(BASE, f"judge_dump_{name}.txt"), "w") as f:
            for r in rows:
                f.write(f"### {r['sid']} | {r['repo']}#{r['number']} | src={r['req_src']}\nTITLE: {r['title']}\n--- REQUEST ---\n{(r['request'] or '(none)')[:REQ_MAX]}\n--- REVIEW (CR) ---\n{r['review']}\n\n")
        df = pd.DataFrame(rows); print(name, len(df)); print(df.req_src.value_counts()); print(pd.crosstab(df.group, df.req_src))

if __name__ == "__main__":
    main()
