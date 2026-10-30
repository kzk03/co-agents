"""pilot の CR ブロック(ghhuman_blocks.jsonl)に「エージェント関与の強さ」を付ける。
- strong: レビュー提出時刻より前のコミットに、コーディングエージェントの trailer / 生成署名がある
  (Claude / Cursor / Codex / Devin / Jules / OpenHands / Aider / Amazon Q / roachdev-claude / Generated with Claude Code)
- weak: trailer は Copilot / Copilot Autofix / gemini-code-assist のみ(GitHub 上で AI レビューの提案を適用した可能性が高い)、
  または強い trailer がレビュー後のコミットにしかない
- none: agent_coauthor=False(extract.py の判定)
実行(humans_md/ で): uv run work/baseline/within_classify.py → work/baseline/within/blocks_agent.jsonl, agent_level.txt
"""
import collections, glob, json, os, re
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/pilot_raw_full"))
STRONG = re.compile(r"(?im)^co-authored-by:.*(claude|anthropic|cursor|codex|openai|devin|jules|paperclip|aider|openhands|"
                    r"amazon q|roachdev-claude)|generated with \[?claude code|🤖 generated with")
blocks = [json.loads(l) for l in open(f"{ROOT}/work/baseline/ghhuman_blocks.jsonl")]
need = {(b["repo"], b["number"]) for b in blocks if b["agent_coauthor"]}
commits = {}
for d in glob.glob(RAW + "/*"):
    repo = os.path.basename(d).replace("__", "/", 1)
    for l in open(d + "/prs_full.jsonl"):
        try:
            j = json.loads(l)
        except json.JSONDecodeError:
            continue
        if (repo, j["number"]) in need:
            commits[(repo, j["number"])] = [(c["commit"].get("committedDate") or "", c["commit"]["message"] or "")
                                            for c in ((j.get("commits") or {}).get("nodes") or [])]
out, cnt = [], collections.Counter()
for b in blocks:
    lvl = "none"
    if b["agent_coauthor"]:
        cs = commits.get((b["repo"], b["number"]), [])
        lvl = "strong" if any(STRONG.search(m) and d and d < b["submittedAt"] for d, m in cs) else "weak"
    b["agent_level"] = lvl; out.append(b); cnt[lvl] += 1
with open(f"{ROOT}/work/baseline/within/blocks_agent.jsonl", "w") as f:
    for b in out:
        f.write(json.dumps(b, ensure_ascii=False) + "\n")
L = [f"CR ブロック数 {dict(cnt)}"]
for lvl in ["strong", "weak", "none"]:
    rs = [b for b in out if b["agent_level"] == lvl]
    oc = collections.Counter(b["outcome"] for b in rs)
    L.append(f"== {lvl}: CR {len(rs)} PR {len({(b['repo'], b['number']) for b in rs})} repo {len({b['repo'] for b in rs})} "
             f"closed率 {oc['closed'] / max(len(rs), 1):.3f}")
    L.append("  repo上位 " + str(collections.Counter(b["repo"] for b in rs).most_common(12)))
s = collections.Counter(b["repo"] for b in out if b["agent_level"] == "strong")
n = collections.Counter(b["repo"] for b in out if b["agent_level"] == "none")
L.append("== strong と none が両方ある repo: " + str(sorted(((r, s[r], n[r]) for r in s if n[r]), key=lambda x: -x[1])))
open(f"{ROOT}/work/baseline/within/agent_level.txt", "w").write("\n".join(L) + "\n"); print("\n".join(L))
