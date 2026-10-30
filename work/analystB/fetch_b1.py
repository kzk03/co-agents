"""B1 用: v1 の 70 件について、PR の base commit 時点の文書(本文)と、CR から 180 日の間の文書の更新コミット、
窓の終わり時点(窓内の最後の更新コミット)の文書本文を GraphQL で取得する。
REST の commits?path=&since=&until= と同じ情報を history(path:, since:, until:) で取る(呼び出し回数節約のため)。
段1: base 時点の本文 + 既定ブランチ上の窓内 history(item 5件 / 呼び出し)
段2: 窓内に更新があった (item, path) について、最後の更新コミット時点の本文
出力: work/analystB/b1_docs.jsonl。uv run python work/analystB/fetch_b1.py {stage1|stage2} [max_calls]"""
import csv, json, os, sys
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ghq import gql, esc, B
ROOT = os.path.abspath(os.path.join(B, "../.."))
PATHS = ["AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md", "CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md", "CONTRIBUTING.rst"]
OUT1 = os.path.join(B, "b1_stage1.jsonl"); OUT2 = os.path.join(B, "b1_stage2.jsonl")


def items():
    v1 = [r["sid"] for r in csv.DictReader(open(os.path.join(ROOT, "work/codebook/coding_merged_v1.csv")))]
    b2 = {r["sid"]: r for r in csv.DictReader(open(os.path.join(B, "b2_rows.csv")))}
    gh = {}
    for l in open(os.path.join(B, "b2_prs.jsonl")):
        j = json.loads(l)
        if j["ok"]: gh[(j["repo"], j["number"])] = j["pr"]
    out = []
    for s in v1:
        r = b2[s]; c = json.load(open(os.path.join(ROOT, f"work/codebook/cache/{s}.json")))
        p = gh.get((r["repo"], int(r["number"])))
        ref = c["ref"] if c["source"].startswith("base.sha") else (p or {}).get("baseRefOid")
        t = datetime.strptime(r["t"][:19], "%Y-%m-%dT%H:%M:%S")
        out.append(dict(sid=s, repo=r["repo"], ref=ref, ref_src=("cache" if c["source"].startswith("base.sha") else "graphql baseRefOid"),
                        since=t.strftime("%Y-%m-%dT%H:%M:%SZ"), until=(t + timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ"), ok_repo=p is not None))
    return out


def stage1(maxc):
    done = {json.loads(l)["sid"] for l in open(OUT1)} if os.path.exists(OUT1) else set()
    todo = [x for x in items() if x["sid"] not in done and x["ok_repo"] and x["ref"]]
    skip = [x["sid"] for x in items() if not (x["ok_repo"] and x["ref"])]
    print("todo", len(todo), "skip(repo 消失)", skip)
    BS = 5; calls = 0
    for i in range(0, len(todo), BS):
        if calls >= maxc: break
        ch = todo[i:i + BS]; parts = []
        for k, x in enumerate(ch):
            o, nm = x["repo"].split("/", 1)
            ob = " ".join(f'b{m}: object(expression:"{x["ref"]}:{p}"){{... on Blob{{text byteSize}}}}' for m, p in enumerate(PATHS))
            hs = " ".join(f'h{m}: history(path:"{p}", since:"{x["since"]}", until:"{x["until"]}", first:50){{totalCount nodes{{oid committedDate messageHeadline}}}}' for m, p in enumerate(PATHS))
            parts.append(f'i{k}: repository(owner:"{esc(o)}", name:"{esc(nm)}"){{ {ob} defaultBranchRef{{name target{{... on Commit{{ {hs} }}}}}} }}')
        j = gql("query { " + " ".join(parts) + " rateLimit{cost remaining} }", "b1s1"); calls += 1
        d = j.get("data") or {}
        with open(OUT1, "a") as f:
            for k, x in enumerate(ch):
                y = d.get(f"i{k}")
                rec = dict(x, ok=y is not None)
                if y:
                    t = ((y.get("defaultBranchRef") or {}).get("target") or {})
                    rec["branch"] = (y.get("defaultBranchRef") or {}).get("name")
                    rec["docs"] = {p: dict(base=(y.get(f"b{m}") or {}).get("text"), base_exists=y.get(f"b{m}") is not None,
                                           hist=(t.get(f"h{m}") or {}).get("nodes", []), n_hist=(t.get(f"h{m}") or {}).get("totalCount"))
                                   for m, p in enumerate(PATHS)}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(i, d.get("rateLimit"), [str(e)[:150] for e in (j.get("errors") or [])][:3], flush=True)


def stage2(maxc):
    s1 = [json.loads(l) for l in open(OUT1)]
    done = {(j["sid"], j["path"]) for j in map(json.loads, open(OUT2))} if os.path.exists(OUT2) else set()
    todo = []
    for x in s1:
        if not x["ok"]: continue
        for p, d in x["docs"].items():
            if d["hist"] and (x["sid"], p) not in done:
                last = max(d["hist"], key=lambda h: h["committedDate"])
                todo.append((x["sid"], x["repo"], p, last["oid"]))
    print("todo", len(todo))
    BS = 8; calls = 0
    for i in range(0, len(todo), BS):
        if calls >= maxc: break
        ch = todo[i:i + BS]
        parts = [f'i{k}: repository(owner:"{esc(r.split("/", 1)[0])}", name:"{esc(r.split("/", 1)[1])}"){{ object(expression:"{oid}:{p}"){{... on Blob{{text byteSize}}}} }}' for k, (s, r, p, oid) in enumerate(ch)]
        j = gql("query { " + " ".join(parts) + " rateLimit{cost remaining} }", "b1s2"); calls += 1
        d = j.get("data") or {}
        with open(OUT2, "a") as f:
            for k, (s, r, p, oid) in enumerate(ch):
                y = d.get(f"i{k}")
                f.write(json.dumps(dict(sid=s, repo=r, path=p, oid=oid, ok=y is not None, exists=(y or {}).get("object") is not None,
                                        text=((y or {}).get("object") or {}).get("text")), ensure_ascii=False) + "\n")
        print(i, d.get("rateLimit"), [str(e)[:150] for e in (j.get("errors") or [])][:3], flush=True)


if __name__ == "__main__":
    {"stage1": stage1, "stage2": stage2}[sys.argv[1]](int(sys.argv[2]) if len(sys.argv) > 2 else 999)
