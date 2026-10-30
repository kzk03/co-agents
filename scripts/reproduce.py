"""HUMANS.md調査 再現スクリプト(2026-10-20)

使い方(humans_md/ で): python3 scripts/reproduce.py [github|gerrit_extract|gerrit_sample]
出力先: outputs/github/, outputs/gerrit/
- github         : GitHub code search で filename:HUMANS.md を最大1000件取得し、ファイル名完全一致分の本文を保存
- gerrit_extract : data/raw_json (OpenStack Gerrit, 232 repo) から人間の Code-Review -1/-2 を抽出
- gerrit_sample  : 層化抽出100件 + review.opendev.org から該当パッチセットのインラインコメントを取得
"""
import base64, collections, glob, hashlib, json, os, random, re, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW = os.path.join(ROOT, "data", "raw_json", "*.json")  # Master_research/data/raw_json へのシンボリックリンク
GH = os.path.join(ROOT, "outputs", "github")
GR = os.path.join(ROOT, "outputs", "gerrit")


def sh(*a):
    return subprocess.run(list(a), capture_output=True, text=True, timeout=60).stdout


def github():
    os.makedirs(os.path.join(GH, "humans_files"), exist_ok=True)
    os.chdir(GH)
    rows = []
    for p in range(1, 11):
        out = sh("gh", "api", "-X", "GET", "search/code", "-f", "q=filename:HUMANS.md",
                 "-f", "per_page=100", "-f", f"page={p}",
                 "--jq", ".items[] | {repo:.repository.full_name, path:.path}")
        rows += [json.loads(l) for l in out.splitlines() if l]
        time.sleep(7)
    seen, out = set(), []
    for r in rows:
        if r["path"].split("/")[-1].lower() != "humans.md" or (r["repo"], r["path"]) in seen:
            continue
        seen.add((r["repo"], r["path"]))
        c = sh("gh", "api", f"repos/{r['repo']}/contents/{r['path']}", "--jq", ".content")
        txt = base64.b64decode(c).decode("utf-8", "replace")
        fn = r["repo"].replace("/", "__") + "__" + r["path"].replace("/", "__")
        open("humans_files/" + fn, "w").write(txt)
        r.update(file=fn, chars=len(txt), sha=hashlib.md5(txt.encode()).hexdigest())
        out.append(r)
    json.dump(out, open("humans_exact.json", "w"), ensure_ascii=False, indent=1)


def gerrit_extract():
    os.makedirs(GR, exist_ok=True)
    os.chdir(GR)
    rows = []
    for f in glob.glob(RAW):
        for c in json.load(open(f)):
            for m in c.get("messages", []):
                a = m.get("author", {})
                if "SERVICE_USER" in a.get("tags", []):
                    continue
                msg = m.get("message", "")
                mm = re.match(r"^Patch Set (\d+):(.*)$", msg.split("\n", 1)[0])
                if not mm or not re.search(r"Code-Review(-1|-2)\b", mm.group(2)):
                    continue
                body = msg.split("\n", 1)[1].strip() if "\n" in msg else ""
                ncm = re.search(r"\((\d+) (?:inline )?comments?\)", body)
                rows.append(dict(project=c["project"], number=c["_number"], change_id=c["id"],
                                 subject=c["subject"], status=c["status"],
                                 owner=c["owner"].get("_account_id"), reviewer=a.get("_account_id"),
                                 is_self=a.get("_account_id") == c["owner"].get("_account_id"),
                                 vote=-2 if "Code-Review-2" in mm.group(2) else -1,
                                 ps=int(mm.group(1)), date=m["date"][:19], body=body,
                                 n_inline=int(ncm.group(1)) if ncm else 0))
    json.dump(rows, open("gerrit_neg_votes_all.json", "w"), ensure_ascii=False)


def gerrit_sample():
    os.chdir(GR)
    random.seed(42)
    rows = [r for r in json.load(open("gerrit_neg_votes_all.json")) if not r["is_self"]]
    era = lambda d: "early" if int(d[:4]) <= 2019 else ("mid" if int(d[:4]) <= 2022 else "late")
    target = {(-1, "early"): 28, (-1, "mid"): 28, (-1, "late"): 29,
              (-2, "early"): 5, (-2, "mid"): 5, (-2, "late"): 5}
    random.shuffle(rows)
    up, ur, cnt, pick = collections.Counter(), collections.Counter(), collections.Counter(), []
    for r in rows:
        k = (r["vote"], era(r["date"]))
        if cnt[k] >= target[k] or up[r["project"]] >= 2 or ur[r["reviewer"]] >= 2:
            continue
        pick.append(r); cnt[k] += 1; up[r["project"]] += 1; ur[r["reviewer"]] += 1
    for i, r in enumerate(pick):
        r["sid"] = f"S{i+1:03d}"
        t = sh("curl", "-s", "--max-time", "30",
               f"https://review.opendev.org/changes/{r['change_id']}/revisions/{r['ps']}/comments")
        com = json.loads(t.split("\n", 1)[1])  # change_id は既にURLエンコード済み
        r["inline"] = [{"path": p, "line": c.get("line"), "message": c["message"]}
                       for p, cs in com.items() for c in cs
                       if c.get("author", {}).get("_account_id") == r["reviewer"]
                       and c.get("updated", "")[:16] <= r["date"][:16]]
        time.sleep(0.3)
    json.dump(pick, open("gerrit_pilot_sample100.json", "w"), ensure_ascii=False, indent=1)
    write_dump(pick)


def write_dump(pick):
    """分類用のテキスト一覧(pilot_dump.txt)"""
    with open("pilot_dump.txt", "w") as f:
        for r in pick:
            b = re.sub(r"\(\d+ (inline )?comments?\)", "", r["body"]).strip().replace("\n", " ")
            f.write(f"### {r['sid']} {r['project']} CR{r['vote']} {r['status']} {r['date'][:10]} | {r['subject'][:90]}\n")
            if b:
                f.write(f"  BODY: {b[:500]}\n")
            for c in (r["inline"] or [])[:6]:
                f.write(f"  [{c['path'].split('/')[-1]}:{c['line']}] " + c["message"].replace("\n", " ")[:350] + "\n")


if __name__ == "__main__":
    {"github": github, "gerrit_extract": gerrit_extract, "gerrit_sample": gerrit_sample}[sys.argv[1]]()
