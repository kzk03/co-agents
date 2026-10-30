"""B2 用: AIDev sample100 と ghhuman sample100 の PR について、現在の状態・close した人・コメント・コミット・サイズ・base oid を取得。
出力: work/analystB/b2_prs.jsonl(1 PR 1行)。uv run python work/analystB/fetch_b2.py [max_calls]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ghq import gql, esc, B
ROOT = os.path.abspath(os.path.join(B, "../.."))
OUT = os.path.join(B, "b2_prs.jsonl")


def targets():
    t = {}
    for x in json.load(open(os.path.join(ROOT, "outputs/aidev/sample100.json"))):
        n = int(x["html_url"].rstrip("/").split("/")[-1]); t[(x["repo"], n)] = 1
    for x in json.load(open(os.path.join(ROOT, "outputs/ghhuman/sample100.json"))):
        t[(x["repo"], int(x["number"]))] = 1
    return sorted(t)


FRAG = ('pullRequest(number:%d){ number state merged mergedAt closedAt createdAt baseRefOid additions deletions changedFiles '
        'author{login __typename} mergedBy{login} '
        'timelineItems(itemTypes:[CLOSED_EVENT,REOPENED_EVENT,CROSS_REFERENCED_EVENT], last:30){nodes{__typename '
        '... on ClosedEvent{createdAt actor{login __typename}} ... on ReopenedEvent{createdAt actor{login}} '
        '... on CrossReferencedEvent{createdAt actor{login} isCrossRepository source{__typename ... on Issue{number createdAt author{login}} ... on PullRequest{number createdAt author{login}}}}}} '
        'comments(first:100){totalCount nodes{author{login __typename} createdAt body}} '
        'reviews(first:100){nodes{author{login __typename} state submittedAt body}} '
        'commits(last:100){totalCount nodes{commit{committedDate authoredDate author{user{login}}}}} }')


def main(maxc):
    done = set()
    if os.path.exists(OUT):
        done = {(j["repo"], j["number"]) for j in map(json.loads, open(OUT))}  # NOT_FOUND も再試行しない
    todo = [t for t in targets() if t not in done]
    print("targets", len(targets()), "todo", len(todo))
    BS = 10; calls = 0
    for i in range(0, len(todo), BS):
        if calls >= maxc:
            break
        ch = todo[i:i + BS]
        parts = [f'p{k}: repository(owner:"{esc(r.split("/")[0])}", name:"{esc(r.split("/", 1)[1])}"){{ {FRAG % n} }}' for k, (r, n) in enumerate(ch)]
        j = gql("query { " + " ".join(parts) + " rateLimit{cost remaining} }", "b2"); calls += 1
        d = j.get("data") or {}
        with open(OUT, "a") as f:
            for k, (r, n) in enumerate(ch):
                x = (d.get(f"p{k}") or {}).get("pullRequest")
                f.write(json.dumps({"repo": r, "number": n, "ok": x is not None, "pr": x}, ensure_ascii=False) + "\n")
        print(i, "rate", d.get("rateLimit"), "errors", [str(e)[:120] for e in (j.get("errors") or [])][:2], flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 999)
