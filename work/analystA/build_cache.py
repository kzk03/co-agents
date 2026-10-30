"""Gerrit 生データ(data/raw_json, 読み取り専用)から T2/T3/T5/T6 用の軽量キャッシュを作る。
各 change について:project, number, status, owner, created, files(ps->[path]),
人間(SERVICE_USER 以外)のメッセージ由来の投票履歴 [(acc, date, ps, CR値 or None, WF値 or None)],
人間メッセージ投稿 [(acc, date)]、labels.all 由来の「期間全体 core」(a1 と同じ定義の再現用)。
実行(humans_md/ で): uv run python work/analystA/build_cache.py → work/analystA/cache.pkl
"""
import glob, json, os, pickle, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HDR = re.compile(r"^Patch Set (\d+):(.*)$")
TOK = re.compile(r"(?<![\w-])(Code-Review|Workflow)([+-]\d)\b")
changes = []
for f in sorted(glob.glob(os.path.join(ROOT, "data/raw_json/*.json"))):
    for c in json.load(open(f)):
        owner = c["owner"].get("_account_id")
        files = {}
        for r in (c.get("revisions") or {}).values():
            files[r["_number"]] = [p for p in (r.get("files") or {}) if not p.startswith("/")]
        votes, msgs = [], []
        for m in c.get("messages", []):
            a = m.get("author") or {}
            if "SERVICE_USER" in (a.get("tags") or []) or a.get("_account_id") is None:
                continue
            acc = a["_account_id"]; d = m["date"][:19]
            tag = m.get("tag") or ""
            if "newPatchSet" not in tag and "newWipPatchSet" not in tag:
                msgs.append((acc, d))
            mm = HDR.match(m.get("message", "").split("\n", 1)[0])
            if not mm:
                continue
            cr = wf = None
            for lab, val in TOK.findall(mm.group(2)):
                if lab == "Code-Review": cr = int(val)
                else: wf = int(val)
            if cr is not None or wf is not None:
                votes.append((acc, d, int(mm.group(1)), cr, wf))
        lab = c.get("labels") or {}
        ever = set()
        for v in (lab.get("Code-Review") or {}).get("all", []):
            if v.get("value") in (2, -2): ever.add(v["_account_id"])
        for v in (lab.get("Workflow") or {}).get("all", []):
            if v.get("value") == 1: ever.add(v["_account_id"])
        changes.append(dict(p=c["project"], n=c["_number"], st=c["status"], owner=owner, created=c["created"][:19],
                            files=files, votes=votes, msgs=msgs, ever=ever))
pickle.dump(changes, open(os.path.join(ROOT, "work/analystA/cache.pkl"), "wb"))
print("changes", len(changes), "projects", len({c["p"] for c in changes}))
print("created range", min(c["created"] for c in changes), max(c["created"] for c in changes))
