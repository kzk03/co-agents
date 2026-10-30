"""pilot/raw_full から「人間作者 PR に対する人間レビュアーの CHANGES_REQUESTED」を抽出する。

実行(humans_md/ で): uv run work/baseline/extract.py
出力: work/baseline/ghhuman_blocks.jsonl(全件)、work/baseline/extract_summary.txt
"""
import collections, glob, json, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/pilot_raw_full"))
OUT = os.path.join(ROOT, "work", "baseline")

BOTPAT = re.compile(r"bot\b|\[bot\]|-bot|bot-|^bot|copilot|devin|codex|cursor|claude|jules|dependabot|renovate|"
                    r"coderabbit|gemini|sourcery|ellipsis|greptile|qodo|sweep|openhands|github-actions|"
                    r"mergify|k8s-ci|codecov|sonarcloud|netlify|vercel|allcontributors|pre-commit-ci|"
                    r"roachdev-claude|paperclip|aider|amazon-q|chatgpt|openai|mintlify|graphite-app", re.I)
# エージェントの co-author trailer / 生成署名
AGENT_TRAILER = re.compile(r"(?im)^co-authored-by:.*(copilot|claude|anthropic|cursor|codex|openai|devin|jules|"
                           r"gemini|paperclip|aider|openhands|sweep|amazon q|roachdev-claude)|"
                           r"generated with \[?claude code|🤖 generated with")


def isbot(login):
    return (not login) or bool(BOTPAT.search(login))


def outcome(p):
    if p["mergedAt"]:
        return "merged"
    if p["closedAt"]:
        return "closed"
    return "open"


def main():
  pass
rows, stat = [], collections.Counter()
for d in sorted(glob.glob(os.path.join(RAW, "*"))):
    repo = os.path.basename(d).replace("__", "/", 1)
    rb = {}
    for l in open(os.path.join(d, "review_bodies.jsonl")):
        j = json.loads(l); rb[j["number"]] = j["reviews"]
    need = {n for n, rv in rb.items() if any(r["state"] == "CHANGES_REQUESTED" for r in rv)}
    prs = {}
    for l in open(os.path.join(d, "prs_full.jsonl")):
        try:
            j = json.loads(l)
        except json.JSONDecodeError:
            stat["prs_badline"] += 1; continue
        if j["number"] in need:
            prs[j["number"]] = j  # 重複行は後勝ち
    for n in need:
        p = prs.get(n)
        crs = [r for r in rb[n] if r["state"] == "CHANGES_REQUESTED"]
        stat["cr_all"] += len(crs)
        if p is None:
            stat["cr_no_pr_meta"] += len(crs); continue
        author = (p.get("author") or {}).get("login")
        if isbot(author):
            stat["cr_drop_bot_author"] += len(crs); continue
        msgs = [c["commit"]["message"] for c in ((p.get("commits") or {}).get("nodes") or [])]
        agent_co = any(AGENT_TRAILER.search(m or "") for m in msgs)
        for i, r in enumerate(crs):
            rev = r.get("author")
            if isbot(rev) or rev == repo.split("/")[0]:  # org 名アカウント(例: home-assistant の CLA/競合 bot)
                stat["cr_drop_bot_reviewer"] += 1; continue
            if rev == author:
                stat["cr_drop_self"] += 1; continue
            body = (r.get("body") or "").strip()
            com = [c for c in (r.get("comments") or []) if (c.get("body") or "").strip()]
            if not body and not com:
                stat["cr_drop_no_text"] += 1; continue
            stat["cr_kept_agent_co" if agent_co else "cr_kept"] += 1
            rows.append(dict(rid=f"{repo}#{n}#{r['submittedAt']}#{i}", repo=repo, number=n, pr_author=author,
                             reviewer=rev, submittedAt=r["submittedAt"], outcome=outcome(p), agent_coauthor=agent_co,
                             n_commits=len(msgs), body=body, comments=com))
with open(os.path.join(OUT, "ghhuman_blocks.jsonl"), "w") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

main = [r for r in rows if not r["agent_coauthor"]]
lines = [f"{k}: {v}" for k, v in sorted(stat.items())]
for nm, rs in [("main(人間作者・agent co-author なし)", main), ("agent_coauthor あり(別扱い)", [r for r in rows if r["agent_coauthor"]])]:
    oc = collections.Counter(r["outcome"] for r in rs)
    lines += [f"== {nm}", f" CR件数 {len(rs)}  PR数 {len({(r['repo'], r['number']) for r in rs})}  repo数 {len({r['repo'] for r in rs})}"
              f"  レビュアー数 {len({r['reviewer'] for r in rs})}",
              f" 結末 {dict(oc)}  closed率 {oc['closed'] / max(len(rs), 1):.3f}",
              f" body空(インラインのみ) {sum(not r['body'] for r in rs)}",
              " repo別上位 " + str(collections.Counter(r['repo'] for r in rs).most_common(10))]
open(os.path.join(OUT, "extract_summary.txt"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
