"""gh api graphql の共通ヘルパ(キャッシュ + 呼び出しログ)。
キャッシュ: work/analystB/cache/<key>.json、ログ: work/analystB/gh_calls.log(1呼び出し1行)。
上限: MAXCALLS(既定 400)を超えたら例外。timeout 90 秒。"""
import datetime, hashlib, json, os, subprocess
B = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(B, "cache"); os.makedirs(C, exist_ok=True)
LOG = os.path.join(B, "gh_calls.log")
MAXCALLS = int(os.environ.get("MAXCALLS", 400))


def ncalls():
    return sum(1 for _ in open(LOG)) if os.path.exists(LOG) else 0


def gql(q, tag):
    key = tag + "_" + hashlib.sha1(q.encode()).hexdigest()[:16]
    fn = os.path.join(C, key + ".json")
    if os.path.exists(fn):
        return json.load(open(fn))
    if ncalls() >= MAXCALLS:
        raise RuntimeError("gh call budget exhausted")
    with open(LOG, "a") as f:
        f.write(f"{datetime.datetime.now().isoformat()} graphql {tag}\n")
    r = subprocess.run(["gh", "api", "graphql", "-f", f"query={q}"], capture_output=True, text=True, timeout=90)
    try:
        j = json.loads(r.stdout)
    except Exception:
        j = {"data": None, "errors": [r.stderr[:300]]}
    if j.get("data"):
        json.dump(j, open(fn, "w"), ensure_ascii=False)
    return j


def esc(s):
    return s.replace('"', '\\"')
