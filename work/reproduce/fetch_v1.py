"""v1: 標本拡張(AIDev H系全件 + C系同数)と条件C 文脈の構築。gh api は cache/ にキャッシュ。
uv run python work/reproduce/fetch_v1.py aidev      # 追加標本の差分・B文脈を data/ に保存(v0 と同じ手順)
uv run python work/reproduce/fetch_v1.py ctxc       # 条件C 文脈(Issue 本文 + レビュー前の PR 上議論)を ctxc/ に保存
"""
import base64, json, os, random, re, subprocess, sys, time
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
W = os.path.join(ROOT, "work/reproduce")
OUT = os.path.join(W, "data"); CTXC = os.path.join(W, "ctxc"); CACHE = os.path.join(W, "cache")
DCACHE = os.path.join(ROOT, "work/delegation/cache")  # 読み取りのみ
for d in (OUT, CTXC, CACHE):
    os.makedirs(d, exist_ok=True)
EXCLUDE_EMPTY = {"G045"}
DIFF_CAP, FILE_CAP, DOC_CAP, ISSUE_CAP, DISC_CAP = 60000, 12000, 6000, 8000, 12000
DOCS = ["README.md", "CONTRIBUTING.md", "AGENTS.md", ".github/copilot-instructions.md", "CLAUDE.md"]


def key(path):
    return re.sub(r"[^A-Za-z0-9]+", "_", path) + ".json"


def gh(path, paginate=False):
    """キャッシュ優先: delegation/cache(読み取り) → reproduce/cache → gh api。エラーもキャッシュして再取得しない。"""
    for d in (DCACHE, CACHE):
        fn = os.path.join(d, key(path))
        if os.path.exists(fn):
            j = json.load(open(fn))
            if isinstance(j, dict) and "_error" in j:
                raise RuntimeError(j["_error"])
            return j
    cmd = ["gh", "api", path]
    if paginate:
        cmd[2:2] = ["--paginate", "--slurp"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    fn = os.path.join(CACHE, key(path))
    if r.returncode != 0:
        json.dump({"_error": r.stderr.strip()[:300]}, open(fn, "w"))
        raise RuntimeError(r.stderr.strip()[:300])
    j = json.loads(r.stdout)
    if paginate:
        j = [x for page in j for x in page]
    json.dump(j, open(fn, "w")); time.sleep(0.2)
    return j


def content(repo, path, ref, cap):
    try:
        j = gh(f"repos/{repo}/contents/{path}?ref={ref}")
        return base64.b64decode(j["content"]).decode("utf-8", "replace")[:cap] if isinstance(j, dict) and j.get("content") else None
    except Exception:
        return None


def build_rec(sid, grp, smp, irr, prs_body, rc, src="aidev"):
    """fetch.py(v0)と同じ手順で1件分の rec を作る。失敗時は例外。"""
    r = smp[sid]; repo = r["repo"]; n = int(r["html_url"].rstrip("/").split("/")[-1])
    rec = dict(sid=sid, grp=grp, cat=irr.loc[sid, "majority"], inf=irr.loc[sid, "majority_inf"], repo=repo, number=n,
               title=r["title"], pr_body=prs_body(r), src=src)
    note = []
    pr = gh(f"repos/{repo}/pulls/{n}"); base = pr["base"]["sha"]
    try:
        cid = gh(f"repos/{repo}/pulls/{n}/reviews/{r['review_id']}")["commit_id"]; note.append("commit=review")
    except Exception as e:
        cid = rc(r["review_id"]); note.append(f"commit=fallback({e})")
    files = None
    if cid:
        try:
            files = gh(f"repos/{repo}/compare/{base}...{cid}?per_page=300")["files"]; note.append("diff=compare@review")
        except Exception as e:
            note.append(f"compare_fail({e})")
    if files is None:
        files = gh(f"repos/{repo}/pulls/{n}/files?per_page=100"); note.append("diff=pulls/files(final)")
        cid = pr["head"]["sha"]
    parts = [f"--- {f['filename']} ({f['status']}, +{f.get('additions')} -{f.get('deletions')})\n" + (f.get("patch") or "[no patch: binary or too large]") for f in files]
    diff = "\n".join(parts)
    rec.update(base=base, commit=cid, n_files=len(files), diff_chars=len(diff), truncated=len(diff) > DIFF_CAP, diff=diff[:DIFF_CAP])
    ctx = {}
    for p in DOCS:
        c = content(repo, p, cid, DOC_CAP)
        if c:
            ctx[p] = c
    mod = sorted([f for f in files if f["status"] == "modified"], key=lambda f: -(f.get("changes") or 0))[:3]
    for f in mod:
        c = content(repo, f["filename"], base, FILE_CAP)
        if c:
            ctx[f"{f['filename']} (base version)"] = c
    rec["context"] = ctx; rec["fetch_note"] = "; ".join(note)
    return rec


def aidev():
    smp = {r["sid"]: r for r in json.load(open(os.path.join(ROOT, "outputs/aidev/sample100.json")))}
    d = pd.read_csv(os.path.join(ROOT, "outputs/aidev/irr/irr_merged.csv")); irr = d.set_index("sid")
    rcp = pd.read_parquet(os.path.join(ROOT, "data/aidev/pr_review_comments.parquet"), columns=["pull_request_review_id", "commit_id"])
    prs = pd.read_parquet(os.path.join(ROOT, "data/aidev/pull_request.parquet"), columns=["id", "body"]).set_index("id")["body"]
    def prs_body(r):
        return prs.get(r["pr_id"]) if r["pr_id"] in prs.index else None
    def rc(rid):
        x = rcp[rcp.pull_request_review_id == rid]; return x.commit_id.iloc[0] if len(x) else None
    pools = {"H": [s for s, m in zip(d.sid, d.majority) if m[0] == "H" and s not in EXCLUDE_EMPTY],
             "C": [s for s, m in zip(d.sid, d.majority) if m in ("C1", "C2", "C3")]}
    have = {f[:-5] for f in os.listdir(OUT) if re.match(r"G\d+\.json$", f)}
    log_fn = os.path.join(OUT, "_fetch_log_v1.json")
    log = json.load(open(log_fn)) if os.path.exists(log_fn) else []
    n_h_ok = None
    for grp in ("H", "C"):
        order = pools[grp][:]; random.Random(20261021).shuffle(order)
        target = len(order) if grp == "H" else n_h_ok   # H は全件、C は H の取得成功数と同数
        got = 0
        for sid in order:
            if got >= target:
                break
            if sid in have:
                got += 1; continue
            if any(x["sid"] == sid and x["status"].startswith("EXCLUDED") for x in log):
                continue
            try:
                rec = build_rec(sid, grp, smp, irr, prs_body, rc)
            except Exception as e:
                log.append(dict(sid=sid, grp=grp, status=f"EXCLUDED: {e}")); print(sid, "EXCLUDED", e); continue
            json.dump(rec, open(os.path.join(OUT, f"{sid}.json"), "w"), ensure_ascii=False, indent=1)
            log.append(dict(sid=sid, grp=grp, status="OK", note=rec["fetch_note"], n_files=rec["n_files"], diff_chars=rec["diff_chars"],
                            truncated=rec["truncated"], ctx=list(rec["context"])))
            print(sid, grp, rec["fetch_note"], rec["n_files"], rec["diff_chars"]); got += 1
        if grp == "H":
            n_h_ok = got
        print(grp, "total", got)
    json.dump(log, open(log_fn, "w"), ensure_ascii=False, indent=1)


def _login(e):
    return ((e.get("user") or e.get("actor") or {}) or {}).get("login")


def ctxc_one(rec, review_id, issue_ref, reviewer):
    """条件C 文脈: (1) リンク Issue の本文、(2) PR 上で対象レビューより前の会話(issue comment と review 本文)。
    対象レビューとそれ以後は含めない。"""
    repo, n = rec["repo"], rec["number"]
    tl = gh(f"repos/{repo}/issues/{n}/timeline?per_page=100", paginate=True)
    tgt = [e for e in tl if e.get("event") == "reviewed" and str(e.get("id")) == str(review_id)]
    if not tgt:
        raise RuntimeError("target review not in timeline")
    t0 = tgt[0]["submitted_at"]
    disc = []; same_rev = 0
    for e in tl:
        ev = e.get("event")
        if ev == "commented":
            ts = e.get("created_at")
        elif ev == "reviewed":
            ts = e.get("submitted_at")
        else:
            continue
        if not ts or ts >= t0 or str(e.get("id")) == str(review_id):
            continue
        body = (e.get("body") or "").strip()
        if not body:
            continue
        who = _login(e)
        same_rev += int(who == reviewer)
        disc.append(f"[{ts} {ev} by {who}{' state=' + e.get('state') if e.get('state') else ''}]\n{body}")
    issue_txt = None
    if isinstance(issue_ref, str) and "#" in issue_ref:
        r_, i = issue_ref.split("#")
        try:
            iss = gh(f"repos/{r_}/issues/{i}")
            issue_txt = f"{issue_ref} (by {iss['user']['login']}): {iss.get('title') or ''}\n{iss.get('body') or ''}"[:ISSUE_CAP]
        except Exception as e:
            issue_txt = None
    d = "\n\n".join(disc)
    return dict(sid=rec["sid"], issue=issue_ref if issue_txt else None, issue_text=issue_txt, review_submitted_at=t0,
                n_disc=len(disc), n_disc_same_reviewer=same_rev, disc_chars=len(d), disc_truncated=len(d) > DISC_CAP,
                discussion=d[-DISC_CAP:] if len(d) > DISC_CAP else d)


def ctxc():
    smp = {r["sid"]: r for r in json.load(open(os.path.join(ROOT, "outputs/aidev/sample100.json")))}
    dt = pd.read_csv(os.path.join(ROOT, "work/delegation/delegation_table.csv")).set_index("sid")
    for f in sorted(os.listdir(OUT)):
        if not re.match(r"G\d+\.json$", f):
            continue
        rec = json.load(open(os.path.join(OUT, f))); sid = rec["sid"]
        out = os.path.join(CTXC, f)
        if os.path.exists(out):
            continue
        s = smp[sid]
        issue = dt.loc[sid, "issue"] if sid in dt.index else None
        try:
            c = ctxc_one(rec, s["review_id"], issue, s["reviewer"])
        except Exception as e:
            c = dict(sid=sid, error=str(e))
        json.dump(c, open(out, "w"), ensure_ascii=False, indent=1)
        print(sid, c.get("issue"), c.get("n_disc"), c.get("n_disc_same_reviewer"), c.get("disc_chars"), c.get("error", ""))


ISSUE_RE = re.compile(r"(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s*:?\s+(?:([\w.-]+/[\w.-]+))?#(\d+)", re.I)
ISSUE_URL_RE = re.compile(r"github\.com/([\w.-]+/[\w.-]+)/issues/(\d+)")
OUT_GH = os.path.join(W, "data_gh"); CTXC_GH = os.path.join(W, "ctxc_gh")


def gh_review(repo, n, reviewer, submitted):
    revs = gh(f"repos/{repo}/pulls/{n}/reviews?per_page=100", paginate=True)
    m = [r for r in revs if (r.get("user") or {}).get("login") == reviewer and r.get("submitted_at") == submitted]
    if not m:
        raise RuntimeError("review not found in pulls/reviews")
    return m[0]


def ghhuman():
    """人間作者 PR(agent_coauthor=False)の H系・C系 各9件。"""
    os.makedirs(OUT_GH, exist_ok=True); os.makedirs(CTXC_GH, exist_ok=True)
    smp = {r["sid"]: r for r in json.load(open(os.path.join(ROOT, "outputs/ghhuman/sample100.json")))}
    d = pd.read_csv(os.path.join(ROOT, "outputs/ghhuman/irr/irr_merged.csv")); irr = d.set_index("sid")
    ok = lambda s: str(smp[s].get("agent_coauthor")) == "False"
    pools = {"H": [s for s, m in zip(d.sid, d.majority) if m[0] == "H" and ok(s)],
             "C": [s for s, m in zip(d.sid, d.majority) if m in ("C1", "C2", "C3") and ok(s)]}
    log_fn = os.path.join(OUT_GH, "_fetch_log.json")
    log = json.load(open(log_fn)) if os.path.exists(log_fn) else []
    have = {f[:-5] for f in os.listdir(OUT_GH) if re.match(r"H\d+\.json$", f)}
    for grp, pool in pools.items():
        order = pool[:]; random.Random(20261021).shuffle(order); got = 0
        print(grp, "pool", len(pool))
        for sid in order:
            if got >= 9:
                break
            if sid in have:
                got += 1; continue
            if any(x["sid"] == sid and x["status"].startswith("EXCLUDED") for x in log):
                continue
            r = smp[sid]; repo, n = r["repo"], int(r["number"])
            try:
                rv = gh_review(repo, n, r["reviewer"], r["submittedAt"])
                pr = gh(f"repos/{repo}/pulls/{n}")
                s2 = dict(r, review_id=rv["id"])
                rec = build_rec(sid, grp, {sid: s2}, irr, lambda x: pr.get("body"), lambda rid: rv.get("commit_id"), src="ghhuman")
                # build_rec は reviews/{id} を個別取得するが、キャッシュされない場合に備え commit は rv から
                rec["review_id"] = rv["id"]; rec["pr_author"] = r["pr_author"]
                body = pr.get("body") or ""
                iss = [(m.group(1) or repo, m.group(2)) for m in ISSUE_RE.finditer(body)] + [(m.group(1), m.group(2)) for m in ISSUE_URL_RE.finditer(body)]
                rec["issue_ref"] = f"{iss[0][0]}#{iss[0][1]}" if iss else None
            except Exception as e:
                log.append(dict(sid=sid, grp=grp, status=f"EXCLUDED: {e}")); print(sid, "EXCLUDED", e); continue
            json.dump(rec, open(os.path.join(OUT_GH, f"{sid}.json"), "w"), ensure_ascii=False, indent=1)
            log.append(dict(sid=sid, grp=grp, status="OK", note=rec["fetch_note"], n_files=rec["n_files"], diff_chars=rec["diff_chars"],
                            truncated=rec["truncated"], ctx=list(rec["context"]), issue=rec["issue_ref"]))
            print(sid, grp, repo, n, rec["fetch_note"], rec["n_files"], rec["diff_chars"], rec["issue_ref"]); got += 1
        print(grp, "total", got)
    json.dump(log, open(log_fn, "w"), ensure_ascii=False, indent=1)
    for f in sorted(os.listdir(OUT_GH)):
        if not re.match(r"H\d+\.json$", f):
            continue
        rec = json.load(open(os.path.join(OUT_GH, f))); out = os.path.join(CTXC_GH, f)
        if os.path.exists(out):
            continue
        try:
            c = ctxc_one(rec, rec["review_id"], rec.get("issue_ref"), smp[rec["sid"]]["reviewer"])
        except Exception as e:
            c = dict(sid=rec["sid"], error=str(e))
        json.dump(c, open(out, "w"), ensure_ascii=False, indent=1)
        print(rec["sid"], c.get("issue"), c.get("n_disc"), c.get("n_disc_same_reviewer"), c.get("disc_chars"), c.get("error", ""))


if __name__ == "__main__":
    {"aidev": aidev, "ctxc": ctxc, "gh": ghhuman}[sys.argv[1]]()
