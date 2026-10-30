"""人間2名の校正用シート(50件、層化、結末・作者種別・既存ラベルを伏せる)。
層: set(aidev/ghhuman)各25件 = 対象70件から v1(私)の群ごとに比例割当 19件 + v0 で C/M/UNK だった件から 6件。
uv run python work/codebook/make_sheet.py"""
import csv, json, os, random, re, subprocess
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")); W = os.path.join(ROOT, "work/codebook")
rng = random.Random(20261021)
me = {r["sid"]: r for r in csv.DictReader(open(os.path.join(W, "coding_merged_v1.csv")))}
def grp(c):
    return "C" if c in ("C1", "C2", "C3", "M") else c.split("-")[0]
def ref_of(repo, n, sid):
    fn = os.path.join(W, "cache", f"{sid}.json")
    if os.path.exists(fn):
        return json.load(open(fn)).get("ref")
    fn = os.path.join(W, "cache", f"{sid}_ref.json")
    if not os.path.exists(fn):
        r = subprocess.run(["gh", "api", f"repos/{repo}/pulls/{n}", "--jq", ".base.sha"], capture_output=True, text=True)
        json.dump({"ref": r.stdout.strip() or None}, open(fn, "w"))
    return json.load(open(fn))["ref"]
picked = []
for name in ("aidev", "ghhuman"):
    smp = {r["sid"]: r for r in json.load(open(os.path.join(ROOT, f"outputs/{name}/sample100.json")))}
    irr = {r["sid"]: r for r in csv.DictReader(open(os.path.join(ROOT, f"outputs/{name}/irr/irr_merged.csv")))}
    tgt = [s for s in me if me[s]["set"] == name]
    bygrp = {}
    for s in tgt:
        bygrp.setdefault(grp(me[s]["me"]), []).append(s)
    # 比例割当(最大剰余)で 19 件、各群最低1件
    quota = {g: max(1, int(19 * len(v) / len(tgt))) for g, v in bygrp.items()}
    rem = sorted(bygrp, key=lambda g: -(19 * len(bygrp[g]) / len(tgt) - int(19 * len(bygrp[g]) / len(tgt))))
    i = 0
    while sum(quota.values()) < 19:
        g = rem[i % len(rem)]
        if quota[g] < len(bygrp[g]): quota[g] += 1
        i += 1
    for g, v in bygrp.items():
        v = sorted(v); rng.shuffle(v); picked += [(name, s, f"v1:{g}") for s in v[:quota[g]]]
    rest = sorted(s for s, r in irr.items() if r["majority"] in ("C1", "C2", "C3", "M", "UNK")); rng.shuffle(rest)
    picked += [(name, s, "v0:C/M/UNK") for s in rest[:6]]
rng.shuffle(picked)
key, out = [], []
out.append("""# HUMANS.md 研究 コードブック v1 校正シート(人間2名用)

- 記入者: ______________  記入日: ______________
- 先に `work/codebook/codebook_v1.md` の「判定手順」と「境界例」を読んでください(実例の sid はこのシートと重なることがあるが、その件の正解とは限らない)。
- 2名は**相談せずに独立に**記入してください。結末(マージ/クローズ)・作者が AI か人間か・既存ラベルは伏せてあります。本文中の `@copilot` などから推測できる場合もありますが、推測した事実は判定に使わないでください。
- 「文書確認」のリンクは PR の base commit 時点のリポジトリです。README / CONTRIBUTING / AGENTS.md / .github/copilot-instructions.md / CLAUDE.md を見て「既に書かれていたか」を判定してください(1件 3 分まで。見つからなければ「書かれていない」で可)。PR ページは結末が見えるので開かないでください。

記入欄:
- **主**: X / C1 / C2 / C3 / M / K-pub / K-priv / R-tech / R-gov / D-dir / D-risk / UNK のどれか1つ
- **副**: 同じ選択肢から0〜1個(なければ空欄)
- **書けたか**: could(事前に一般的な文として書けた)/ no(その場でしか出ない)/ -(C・X・UNK)
- **書かれていたか**: yes / partial / no / 見られない(K・R・D のときだけ)
- **確信度**: 1(迷った)〜 3(迷わない)
""")
for i, (name, sid, stratum) in enumerate(picked, 1):
    smp = {r["sid"]: r for r in json.load(open(os.path.join(ROOT, f"outputs/{name}/sample100.json")))}
    r = smp[sid]; repo = r["repo"]; n = int(r.get("number") or r["html_url"].rstrip("/").split("/")[-1])
    ref = ref_of(repo, n, sid)
    body = r.get("body"); body = "" if body is None or (isinstance(body, float)) else str(body)
    inl = r.get("inline") or r.get("comments") or []
    lines = [f"## Q{i:02d}  {repo} | {r['title']}", ""]
    lines.append(f"文書確認: https://github.com/{repo}/tree/{ref}" if ref else "文書確認: (リポジトリにアクセスできない)")
    lines.append("")
    lines.append("**レビュー本文**: " + (body.strip().replace("\n", " ") if body.strip() else "(なし)"))
    for c in inl:
        t = (c.get("body") or "").strip().replace("\n", " ")
        if len(t) > 900: t = t[:900] + " …"
        lines.append(f"- `[{os.path.basename(c.get('path') or '')}]` {t}")
    lines += ["", "| 主 | 副 | 書けたか | 書かれていたか | 確信度 | メモ |", "|---|---|---|---|---|---|", "|  |  |  |  |  |  |", ""]
    out.append("\n".join(lines))
    key.append(dict(q=f"Q{i:02d}", set=name, sid=sid, stratum=stratum, outcome=r.get("outcome"),
                    me=me.get(sid, {}).get("me", ""), sonnet=me.get(sid, {}).get("sonnet", ""), ref=ref))
open(os.path.join(W, "human_sheet.md"), "w").write("\n".join(out))
with open(os.path.join(W, "human_sheet_key.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(key[0])); w.writeheader(); w.writerows(key)
import collections
print(len(key), collections.Counter((k["set"], k["stratum"]) for k in key))
