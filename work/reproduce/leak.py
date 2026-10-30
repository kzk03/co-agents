"""PR 本文のリーク点検: データセットの PR 本文(pull_request.parquet)がレビュー後に編集された版かを、
GraphQL の userContentEdits(各編集時点の本文全文)で確認し、レビュー時点の本文を復元する。gh api は cache/ にキャッシュ。
uv run python work/reproduce/leak.py  → results/leakage_v1.csv, data_at_review_body/<sid>.txt
"""
import glob, json, os, re, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
W = os.path.join(ROOT, "work/reproduce"); CACHE = os.path.join(W, "cache"); OUTB = os.path.join(W, "data_at_review_body")
os.makedirs(OUTB, exist_ok=True)
Q = 'query($o:String!,$n:String!,$num:Int!){repository(owner:$o,name:$n){pullRequest(number:$num){createdAt lastEditedAt body userContentEdits(first:100){totalCount nodes{editedAt diff}}}}}'


def gql(repo, num):
    fn = os.path.join(CACHE, f"graphql_edits_{repo.replace('/', '_')}_{num}.json")
    if os.path.exists(fn):
        return json.load(open(fn))
    o, n = repo.split("/")
    r = subprocess.run(["gh", "api", "graphql", "-f", f"query={Q}", "-F", f"o={o}", "-F", f"n={n}", "-F", f"num={num}"], capture_output=True, text=True)
    j = json.loads(r.stdout) if r.returncode == 0 else {"_error": r.stderr[:300]}
    json.dump(j, open(fn, "w"))
    return j


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def main():
    import pandas as pd
    rows = []
    for f in sorted(glob.glob(os.path.join(W, "data", "G[0-9]*.json"))):
        rec = json.load(open(f)); sid = rec["sid"]
        c = json.load(open(os.path.join(W, "ctxc", f"{sid}.json")))
        t0 = c.get("review_submitted_at")
        j = gql(rec["repo"], rec["number"])
        if "_error" in j or not j.get("data"):
            rows.append(dict(sid=sid, error=j.get("_error"))); continue
        pr = j["data"]["repository"]["pullRequest"]
        edits = sorted(pr["userContentEdits"]["nodes"], key=lambda e: e["editedAt"])
        before = [e for e in edits if e["editedAt"] <= t0]
        after = [e for e in edits if e["editedAt"] > t0]
        body_rev = before[-1]["diff"] if before else (pr["body"] if not edits else None)
        if body_rev is not None:
            open(os.path.join(OUTB, f"{sid}.txt"), "w").write(body_rev)
        rows.append(dict(sid=sid, grp=rec["grp"], review_at=t0, pr_created=pr["createdAt"], n_edits=pr["userContentEdits"]["totalCount"],
                         n_edits_after_review=len(after), dataset_body_eq_at_review=(norm(rec["pr_body"]) == norm(body_rev)) if body_rev is not None else None,
                         dataset_body_eq_current=norm(rec["pr_body"]) == norm(pr["body"]), len_dataset=len(rec["pr_body"] or ""),
                         len_at_review=len(body_rev) if body_rev is not None else None))
    df = pd.DataFrame(rows); df.to_csv(os.path.join(W, "results/leakage_v1.csv"), index=False)
    print(df.to_string())
    print("\nデータセット本文 == レビュー時点本文:", df.dataset_body_eq_at_review.value_counts(dropna=False).to_dict())
    print("群別(False=レビュー後に編集された本文が入力に入った):\n", pd.crosstab(df.grp, df.dataset_body_eq_at_review.fillna("NA")))


if __name__ == "__main__":
    main()
