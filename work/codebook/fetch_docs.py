"""対象 70 件について、PR の base commit 時点の文書を取得(キャッシュ: work/codebook/cache/)。
reproduce の data/*.json に context がある件はそれを使う(注: そちらはレビュー時点の head、各 6,000 字で打ち切り)。
uv run python work/codebook/fetch_docs.py"""
import base64, json, os, subprocess
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
C = os.path.join(ROOT, "work/codebook/cache"); os.makedirs(C, exist_ok=True)
DOCS = ["README.md", "README.rst", "CONTRIBUTING.md", ".github/CONTRIBUTING.md", "CONTRIBUTING.rst", "docs/CONTRIBUTING.md",
        "AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md"]

def gh(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return json.loads(r.stdout)

def main():
    tg = json.load(open(os.path.join(ROOT, "work/codebook/targets.json")))
    smp = {}
    for name in ["aidev", "ghhuman"]:
        for r in json.load(open(os.path.join(ROOT, f"outputs/{name}/sample100.json"))):
            smp[r["sid"]] = r
    for t in tg:
        sid = t["sid"]; fn = os.path.join(C, f"{sid}.json")
        if os.path.exists(fn):
            continue
        rp = os.path.join(ROOT, f"work/reproduce/data/{sid}.json")
        if os.path.exists(rp):
            d = json.load(open(rp))
            ctx = {k: v for k, v in d["context"].items() if "(base version)" not in k}
            json.dump(dict(sid=sid, repo=d["repo"], ref=d["commit"], source="reproduce(head@review, 6000字打切)", docs=ctx), open(fn, "w"), ensure_ascii=False)
            print(sid, "reproduce", list(ctx)); continue
        r = smp[sid]; repo = r["repo"]; n = int(r.get("number") or r["html_url"].rstrip("/").split("/")[-1])
        try:
            pr = gh(f"repos/{repo}/pulls/{n}"); ref = pr["base"]["sha"]
        except Exception as e:
            json.dump(dict(sid=sid, repo=repo, ref=None, source=f"FAIL {e}", docs={}), open(fn, "w")); print(sid, "FAIL", e); continue
        docs = {}
        for p in DOCS:
            try:
                j = gh(f"repos/{repo}/contents/{p}?ref={ref}")
                if isinstance(j, dict) and j.get("content"):
                    docs[p] = base64.b64decode(j["content"]).decode("utf-8", "replace")
            except Exception:
                pass
        json.dump(dict(sid=sid, repo=repo, ref=ref, source="base.sha(pulls API)", docs=docs), open(fn, "w"), ensure_ascii=False)
        print(sid, repo, ref[:8], {k: len(v) for k, v in docs.items()})

if __name__ == "__main__":
    main()
