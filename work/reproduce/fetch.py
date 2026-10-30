"""標本抽出 + レビュー時点の差分・文脈取得。 uv run python work/reproduce/fetch.py"""
import base64, json, os, random, subprocess
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
OUT = os.path.join(ROOT, "work/reproduce/data"); os.makedirs(OUT, exist_ok=True)
EXCLUDE_EMPTY = {"G045"}  # "Abandoning this pending review" のみ
DIFF_CAP, FILE_CAP, DOC_CAP = 60000, 12000, 6000
DOCS = ["README.md", "CONTRIBUTING.md", "AGENTS.md", ".github/copilot-instructions.md", "CLAUDE.md"]


def gh(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:300])
    return json.loads(r.stdout)


def content(repo, path, ref, cap):
    try:
        j = gh(f"repos/{repo}/contents/{path}?ref={ref}")
        return base64.b64decode(j["content"]).decode("utf-8", "replace")[:cap] if isinstance(j, dict) and j.get("content") else None
    except Exception:
        return None


def main():
    smp = {r["sid"]: r for r in json.load(open(os.path.join(ROOT, "outputs/aidev/sample100.json")))}
    d = pd.read_csv(os.path.join(ROOT, "outputs/aidev/irr/irr_merged.csv"))
    rc = pd.read_parquet(os.path.join(ROOT, "data/aidev/pr_review_comments.parquet"), columns=["pull_request_review_id", "commit_id", "original_commit_id"])
    prs = pd.read_parquet(os.path.join(ROOT, "data/aidev/pull_request.parquet"), columns=["id", "body"]).set_index("id")["body"]
    pools = {"H": [s for s, m in zip(d.sid, d.majority) if m[0] == "H" and s not in EXCLUDE_EMPTY],
             "C": [s for s, m in zip(d.sid, d.majority) if m in ("C1", "C2", "C3")]}
    log = []
    for grp, pool in pools.items():
        order = pool[:]; random.Random(20261021).shuffle(order)
        got = 0
        for sid in order:
            if got >= 9:
                break
            r = smp[sid]; repo = r["repo"]; n = int(r["html_url"].rstrip("/").split("/")[-1])
            rec = dict(sid=sid, grp=grp, cat=d.set_index("sid").loc[sid, "majority"], inf=d.set_index("sid").loc[sid, "majority_inf"],
                       repo=repo, number=n, title=r["title"], pr_body=prs.get(r["pr_id"]) if r["pr_id"] in prs.index else None)
            note = []
            try:
                pr = gh(f"repos/{repo}/pulls/{n}"); base = pr["base"]["sha"]
                try:
                    cid = gh(f"repos/{repo}/pulls/{n}/reviews/{r['review_id']}")["commit_id"]; note.append("commit=review")
                except Exception as e:
                    x = rc[rc.pull_request_review_id == r["review_id"]]
                    cid = x.commit_id.iloc[0] if len(x) else None; note.append(f"commit=parquet({e})")
                files = None
                if cid:
                    try:
                        files = gh(f"repos/{repo}/compare/{base}...{cid}?per_page=300")["files"]; note.append("diff=compare@review")
                    except Exception as e:
                        note.append(f"compare_fail({e})")
                if files is None:
                    files = gh(f"repos/{repo}/pulls/{n}/files?per_page=100"); note.append("diff=pulls/files(final)")
                    cid = pr["head"]["sha"]
            except Exception as e:
                log.append(dict(sid=sid, grp=grp, status=f"EXCLUDED: {e}")); print(sid, "EXCLUDED", e); continue
            parts = []
            for f in files:
                parts.append(f"--- {f['filename']} ({f['status']}, +{f.get('additions')} -{f.get('deletions')})\n" + (f.get("patch") or "[no patch: binary or too large]"))
            diff = "\n".join(parts)
            rec.update(base=base, commit=cid, n_files=len(files), diff_chars=len(diff), truncated=len(diff) > DIFF_CAP, diff=diff[:DIFF_CAP])
            # 条件B 文脈
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
            json.dump(rec, open(os.path.join(OUT, f"{sid}.json"), "w"), ensure_ascii=False, indent=1)
            log.append(dict(sid=sid, grp=grp, status="OK", note=rec["fetch_note"], n_files=len(files), diff_chars=len(diff), truncated=rec["truncated"], ctx=list(ctx)))
            print(sid, grp, rec["fetch_note"], len(files), len(diff), list(ctx)); got += 1
    json.dump(log, open(os.path.join(OUT, "_fetch_log.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
