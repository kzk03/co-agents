"""分析6: 実在 HUMANS.md(186件)のうち AI 文脈のもの(既存の種類 A/G/M)を、行(箇条書き・文)単位のキーワード辞書で K/R/D/O に粗く振り分ける。
種類は work/codebook/humans_files_types.csv(Opus が読んで付けた)。辞書は下の DICT(1行が複数カテゴリに当たってよい)。
uv run python work/explore/a6_humansmd.py"""
import os, re, csv, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
F = os.path.join(ROOT, "outputs/github/humans_files")
DICT = {
 "K": r"\b(context|background|history|historical|domain knowledge|tribal|why we|rationale|customer|stakeholder|who to ask|ask (?:a|the) human|knows?\b|knowledge|intent|business)\b",
 "R": r"\b(must|never|always|do not|don't|convention|style guide|rule|rules|policy|policies|guideline|guidelines|required|forbidden|not allowed|only (?:a|the) human)\b",
 "D": r"\b(decide|decides|decision|decisions|approve|approves|approval|sign[- ]off|judg(?:e)?ment|choose|prioriti[sz]e|priority|priorities|trade-?offs?|risk|risky|accountab\w*|responsib\w*|own(?:s|er|ership)?\b|final say|veto)\b",
 "O": r"\b(credential|credentials|api key|secret|secrets|password|token|deploy|deployment|production|billing|payment|physical|hardware|account|accounts|legal|license|licence)\b",
}
RX = {k: re.compile(v, re.I) for k, v in DICT.items()}
types = {r["file"]: r for r in csv.DictReader(open(os.path.join(ROOT, "work/codebook/humans_files_types.csv")))}
out = []
def p(s): out.append(s); print(s)
p("種類: " + str(collections.Counter(r["type"] for r in types.values())))
agg = collections.defaultdict(lambda: collections.Counter()); filehit = collections.defaultdict(lambda: collections.Counter()); nfile = collections.Counter(); nline = collections.Counter()
rows = []
for fn, r in types.items():
    t = r["type"]
    if t not in ("A", "G", "M"): continue
    txt = open(os.path.join(F, fn), errors="replace").read()
    lines = [l.strip() for l in txt.splitlines() if len(l.strip()) > 15 and not l.strip().startswith(("```", "|---", "<!--"))]
    nfile[t] += 1; nline[t] += len(lines)
    seen = collections.Counter()
    for l in lines:
        hit = [k for k, rx in RX.items() if rx.search(l)]
        for k in hit: agg[t][k] += 1; seen[k] += 1
        if not hit: agg[t]["(なし)"] += 1
    for k in seen: filehit[t][k] += 1
    rows.append(dict(file=fn, type=t, lines=len(lines), **{k: seen[k] for k in DICT}))
NAME = {"A": "責任分担型", "G": "協働ガイド型", "M": "人間向け説明書型"}
p("\n== 行単位(長さ>15字の行)。カテゴリごとの該当行数 / 全行数")
for t in ("A", "G", "M"):
    p(f" {t} {NAME[t]}: files {nfile[t]} lines {nline[t]} | " + "  ".join(f"{k} {agg[t][k]} ({agg[t][k]/max(nline[t],1):.2f})" for k in list(DICT) + ["(なし)"]))
p("\n== ファイル単位:そのカテゴリの行を1つ以上含むファイル数")
for t in ("A", "G", "M"):
    p(f" {t}: " + "  ".join(f"{k} {filehit[t][k]}/{nfile[t]}" for k in DICT))
# 優勢カテゴリ(K/R/D のうち最多)
p("\n== ファイルごとの K/R/D 最多カテゴリ(同数は併記)")
for t in ("A", "G", "M"):
    c = collections.Counter()
    for r in rows:
        if r["type"] != t: continue
        m = max(r["K"], r["R"], r["D"])
        c["(該当なし)" if m == 0 else "+".join(k for k in "KRD" if r[k] == m)] += 1
    p(f" {t}: {dict(c)}")
with open(os.path.join(ROOT, "work/explore/a6_humansmd_files.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
p("\n辞書: " + "; ".join(f"{k}={v}" for k, v in DICT.items()))
open(os.path.join(ROOT, "work/explore/a6_humansmd.out"), "w").write("\n".join(out) + "\n")
