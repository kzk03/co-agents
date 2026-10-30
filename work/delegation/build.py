"""Build per-PR requester / request-text table from cache. Output: delegation_table.csv, dump_requests.txt"""
import json, os, re
import pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(BASE, "../.."))
CACHE = os.path.join(BASE, "cache")
def load(path):
    fn = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]+", "_", path) + ".json")
    if not os.path.exists(fn): return None
    d = json.load(open(fn))
    return None if isinstance(d, dict) and "_error" in d else d
ISSUE_RE = re.compile(r"(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s*:?\s+(?:([\w.-]+/[\w.-]+))?#(\d+)", re.I)
ISSUE_URL_RE = re.compile(r"github\.com/([\w.-]+/[\w.-]+)/issues/(\d+)")
BOTS = {"Copilot", "copilot-swe-agent[bot]", "devin-ai-integration[bot]", "google-labs-jules[bot]"}
# Devin "Requested by" -> reviewer identity, judged manually from name/email (see REPORT)
DEVIN_MANUAL = {"G004": "scsmithr", "G029": "Micah Stairs (not mogery)", "G036": "davidgomes?", "G058": "danielinux (daniele@wolfssl.com)",
                "G062": "martinnormark", "G066": "penalosa", "G082": "aaronsteers", "G085": "whitphx?"}

def section(body, key):
    m = re.search(key + r".*?\n(.*?)(</details>|\Z)", body, re.S | re.I)
    return m.group(1).strip() if m else None

rows = []; dump = []
s = json.load(open(os.path.join(ROOT, "outputs/aidev/sample100.json")))
irr = pd.read_csv(os.path.join(ROOT, "outputs/aidev/irr/irr_merged.csv")).set_index("sid")
for x in s:
    m = re.match(r"https://github.com/([^/]+/[^/]+)/pull/(\d+)", x["html_url"]); repo, n = m.group(1), m.group(2)
    pr = load(f"repos/{repo}/pulls/{n}"); tl = load(f"repos/{repo}/issues/{n}/timeline?per_page=100") or []
    row = dict(sid=x["sid"], agent=x["agent"], repo=repo, number=int(n), stratum=x["stratum"], outcome=x["outcome"],
               reviewer=x["reviewer"], majority=irr.loc[x["sid"], "majority"], available=pr is not None)
    req = None; req_src = None; text = None; text_src = None; issue_ref = None
    if pr is not None:
        body = pr.get("body") or ""
        author = pr["user"]["login"]
        # requester
        ws = [e for e in tl if e.get("event") == "copilot_work_started"]
        if ws:
            req = ws[0]["actor"]["login"]; req_src = "copilot_work_started"
        elif author not in BOTS:
            req = author; req_src = "pr_author"
        elif x["sid"] in DEVIN_MANUAL:
            req = DEVIN_MANUAL[x["sid"]]; req_src = "devin_requested_by(manual)"
        else:
            hs = [a["login"] for a in pr.get("assignees", []) if a["login"] not in BOTS]
            if hs: req = hs[0]; req_src = "pr_assignee"
        row["copilot_requesters"] = ";".join(sorted({e["actor"]["login"] for e in ws}))
        # linked issues
        cands = []
        for mm in ISSUE_RE.finditer(body): cands.append((mm.group(1) or repo, mm.group(2)))
        for mm in ISSUE_URL_RE.finditer(body): cands.append((mm.group(1), mm.group(2)))
        for ev in tl:
            if ev.get("event") == "cross-referenced":
                src = (ev.get("source") or {}).get("issue") or {}
                mm = ISSUE_URL_RE.search(src.get("html_url", "") or "")
                if mm and "pull_request" not in src: cands.append((mm.group(1), mm.group(2)))
        best = None
        for r_, i in dict.fromkeys(cands):
            iss = load(f"repos/{r_}/issues/{i}"); itl = load(f"repos/{r_}/issues/{i}/timeline?per_page=100") or []
            if not iss or iss.get("created_at", "9") > pr["created_at"]: continue
            assigned_copilot = [e for e in itl if e.get("event") == "assigned" and (e.get("assignee") or {}).get("login") == "Copilot"]
            score = 2 if assigned_copilot else 1
            if best is None or score > best[0]:
                best = (score, r_, i, iss, assigned_copilot)
        if best:
            _, r_, i, iss, ac = best
            issue_ref = f"{r_}#{i}"; text = (iss.get("title") or "") + "\n" + (iss.get("body") or ""); text_src = "issue"
            row["issue_author"] = iss["user"]["login"]
            row["issue_assigner_copilot"] = ac[0]["actor"]["login"] if ac else None
            if req is None and ac: req = ac[0]["actor"]["login"]; req_src = "issue_assign"
        if text is None:
            for key in ["Original prompt", "Original issue description", "Original description"]:
                t = section(body, key)
                if t: text, text_src = t, "pr_body:" + key; break
        if text is None and x["agent"] != "Copilot":
            text, text_src = body, "pr_body(agent/human-written)"
    row.update(requester=req, requester_src=req_src, issue=issue_ref, req_text_src=text_src,
               req_text_len=len(text) if text else 0)
    rq = (req or "").split(" ")[0].rstrip("?")
    row["reviewer_is_requester"] = None if req is None else (x["reviewer"] == rq)
    row["reviewer_drove_agent"] = x["reviewer"] in (row.get("copilot_requesters") or "").split(";")
    row["reviewer_is_issue_author"] = (row.get("issue_author") == x["reviewer"]) if issue_ref else None
    rows.append(row)
    rev = "BODY: " + str(x.get("body"))[:1200] + "\n" + "\n".join(f"[{c['path']}] {c['body'][:500]}" for c in x["inline"][:5])
    dump.append(f"### {x['sid']} | {x['agent']} | {repo}#{n} | reviewer={x['reviewer']} | requester={req} | src={text_src}\nTITLE: {x['title']}\n--- REQUEST ---\n{(text or '(none)')[:3000]}\n--- REVIEW (CR) ---\n{rev[:2000]}\n")
df = pd.DataFrame(rows); df.to_csv(os.path.join(BASE, "delegation_table.csv"), index=False)
open(os.path.join(BASE, "dump_requests.txt"), "w").write("\n".join(dump))
print(df.requester_src.value_counts(dropna=False)); print(df.req_text_src.value_counts(dropna=False)); print(df.reviewer_is_requester.value_counts(dropna=False))
