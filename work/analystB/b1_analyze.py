"""B1: 文書による被覆。v1 の 70 件について
 (1) base 時点の AGENTS.md / CLAUDE.md / .github/copilot-instructions.md / CONTRIBUTING(.md/.rst、.github/・docs/ 配下)の有無
 (2) 書かれていたか(work/codebook/doc_status.csv の既存判定 + sonnet 判定を集計し直す)
 (3) CR から 180 日以内の更新(既定ブランチの history(path, since, until))と、関連内容の追加(キーワード法)
キーワード法: レビュアーの本文・インライン(targets.json の text からヘッダ行=タイトルを除く)を英字トークン化
  (長さ4以上、ストップワード除去、小文字化)。窓の最後の更新時点の本文で「base に無かった行」(行の集合差)を追加行とし、
  追加行に現れ、かつ base の本文全体には無かったキーワードの異なり数を数える。2 語以上 → 「関連内容が足された」。
  偽陽性の目安: 他の件のキーワード集合を同じ差分に当てた場合の陽性率(並べ替え基準)を併記。
出力: work/analystB/b1_rows.csv、標準出力(b1.out)。uv run python work/analystB/b1_analyze.py > work/analystB/b1.out"""
import collections, csv, json, os, re
import numpy as np
B = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(B, "../.."))
AG = ["AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md"]
CO = ["CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md", "CONTRIBUTING.rst"]
TODAY = "2026-10-27"
STOP = set("""this that with from have will would should could there their they them then than what when where which while your yours
were been being into onto also just like only some such more most much many very here these those does doing done make made making
need needs please thanks thank think want using used uses about after before again because between both each other same over under
change changes changed code file files line lines function method class test tests pull request review comment comments copilot agent
instead already still since well even sure good better maybe might must shall cannot dont doesn isn aren wasn shouldn wouldn couldn
let's lets look looks seems seem thing things way ways part case cases able work works working into upon what's it's that's there's
http https github com www html blob main master tree issue issues commit commits added adding remove removed update updated""".split())
tok = lambda s: {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_\-]{3,}", s)} - STOP

v1 = {r["sid"]: r for r in csv.DictReader(open(os.path.join(ROOT, "work/codebook/coding_merged_v1.csv")))}
ds = {r["sid"]: r for r in csv.DictReader(open(os.path.join(ROOT, "work/codebook/doc_status.csv")))}
tg = {t["sid"]: t for t in json.load(open(os.path.join(ROOT, "work/codebook/targets.json")))}
s1 = {j["sid"]: j for j in map(json.loads, open(os.path.join(B, "b1_stage1.jsonl")))}
s2 = {(j["sid"], j["path"]): j for j in map(json.loads, open(os.path.join(B, "b1_stage2.jsonl")))}
b2 = {r["sid"]: r for r in csv.DictReader(open(os.path.join(B, "b2_rows.csv")))}
cache = {s: json.load(open(os.path.join(ROOT, f"work/codebook/cache/{s}.json"))) for s in v1}

def kw(sid):
    lines = tg[sid]["text"].split("\n")[1:]
    txt = "\n".join(re.sub(r"^\s*(BODY:|\[[^\]]*\])", "", l) for l in lines)
    return tok(txt)

def diffs(sid):
    """(path, base_text, end_text) 窓内に更新があったもの"""
    out = []
    x = s1.get(sid)
    if not x or not x["ok"]: return out
    for p, d in x["docs"].items():
        if d["hist"] and (sid, p) in s2:
            out.append((p, d["base"] or "", s2[(sid, p)]["text"] or ""))
    return out

def hits(keys, dl):
    h = set()
    for p, base, end in dl:
        bl = {l.strip() for l in base.splitlines()}
        added = "\n".join(l for l in end.splitlines() if l.strip() and l.strip() not in bl)
        h |= (keys & tok(added)) - tok(base)
    return h

ALLK = {}
def strict(sid, h):
    """同じ差分に他 repo の件のキーワードを当てたヒット数の 95 パーセンタイルを超えるか"""
    dl = diffs(sid)
    if not dl: return False
    other = [len(hits(ALLK[o], dl)) for o in ALLK if o != sid and REPO[o] != REPO[sid]]
    return len(h) >= 2 and len(h) > np.quantile(other, .95)
grp = lambda c: c.split("-")[0] if c[:1] in "KRD" else ("C" if c[:1] in "CM" else c)
REPO = {s: b2[s]["repo"] for s in v1}
ALLK.update({s: kw(s) for s in v1})
rows = []
for s, r in v1.items():
    x = s1.get(s); ok = bool(x and x["ok"])
    ex = lambda ps: (None if not ok else any(x["docs"][p]["base_exists"] for p in ps))
    upd = lambda ps: (None if not ok else any(x["docs"][p]["hist"] for p in ps))
    new = lambda ps: (None if not ok else any(x["docs"][p]["hist"] and not x["docs"][p]["base_exists"] for p in ps))
    until = x["until"] if x else ""
    dl = diffs(s); h = hits(kw(s), dl)
    rows.append(dict(set=r["set"], sid=s, repo=b2[s]["repo"], v1=r["me"], g=grp(r["me"]), outcome_now=b2[s]["state_now"], b2cls=b2[s]["cls"],
                     ok=ok, ref_src=(x or {}).get("ref_src"), agentdoc_base=ex(AG), contrib_base=ex(CO), anydoc_base=ex(AG + CO),
                     doc_status=ds[s]["doc"], sonnet_written=ds[s]["sonnet_written"],
                     window_complete=(until[:10] <= TODAY) if until else None, window_until=until[:10],
                     upd_agentdoc=upd(AG), upd_contrib=upd(CO), upd_any=upd(AG + CO), new_agentdoc=new(AG),
                     n_upd_commits=(sum(len(x["docs"][p]["hist"]) for p in AG + CO) if ok else None),
                     kw_n=len(kw(s)), kw_hits=len(h), kw_hit_words=" ".join(sorted(h)), related_added=(len(h) >= 2) if ok else None,
                     related_strict=strict(s, h) if ok else None))
with open(os.path.join(B, "b1_rows.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

# 既存キャッシュとの有無の突合(base.sha 由来のもの)
mm = []
for r in rows:
    c = cache[r["sid"]]
    if r["ok"] and c["source"].startswith("base.sha"):
        cx = any(p in c["docs"] for p in AG + CO)
        if cx != r["anydoc_base"]: mm.append(r["sid"])
print("取得:", collections.Counter((r["ok"], r["ref_src"]) for r in rows), " 既存キャッシュ(base.sha)と文書有無の不一致", mm)

CATS = ["C", "K-pub", "K-priv", "R-tech", "R-gov", "D-dir", "D-risk", "X"]
key = lambda r: "C" if r["g"] == "C" else r["v1"]
pct = lambda a, b: f"{a}/{b}" + (f" ({a / b:.2f})" if b else "")
print("\n== (1)(2) カテゴリ別: base 時点の文書あり / 書かれていた(written-repo)/ 外部に書かれていた / sonnet yes|partial")
print(f"{'cat':7} {'n':>3} {'取得':>4} {'AGENTS系あり':>14} {'CONTRIBUTINGあり':>16} {'いずれかあり':>14} {'written-repo':>13} {'elsewhere':>9} {'sonnet yes/partial':>18}")
def line(lab, ss):
    o = [r for r in ss if r["ok"]]
    print(f"{lab:7} {len(ss):>3} {len(o):>4} {pct(sum(r['agentdoc_base'] for r in o), len(o)):>14} {pct(sum(r['contrib_base'] for r in o), len(o)):>16} "
          f"{pct(sum(r['anydoc_base'] for r in o), len(o)):>14} {pct(sum(r['doc_status']=='written-repo' for r in ss), len(ss)):>13} "
          f"{sum(r['doc_status']=='written-elsewhere' for r in ss):>9} {sum(r['sonnet_written'] in ('yes','partial') for r in ss):>8}/{sum(bool(r['sonnet_written']) for r in ss)}")
for c in CATS:
    line(c, [r for r in rows if key(r) == c])
for lab, gs in (("K計", "K"), ("R計", "R"), ("D計", "D")):
    line(lab, [r for r in rows if r["g"] == gs])
line("KRD計", [r for r in rows if r["g"] in "KRD" and r["g"]])
line("全体", rows)
for nm in ("aidev", "ghhuman"):
    line(nm[:7], [r for r in rows if r["set"] == nm])
# repo 単位
for g in ("C", "K", "R", "D"):
    rp = {r["repo"]: r["anydoc_base"] for r in rows if r["g"] == g and r["ok"]}
    ra = {r["repo"]: r["agentdoc_base"] for r in rows if r["g"] == g and r["ok"]}
    print(f"repo 単位 {g}: いずれかあり {sum(rp.values())}/{len(rp)}  AGENTS系あり {sum(ra.values())}/{len(ra)}")

print("\n== 書かれていたのに無視された件(doc_status=written-repo、または sonnet=yes)")
for r in rows:
    if r["doc_status"] == "written-repo" or r["sonnet_written"] == "yes":
        print(f" {r['sid']} {r['repo']} v1={r['v1']} doc_status={r['doc_status']} sonnet={r['sonnet_written']} 現在の結末={r['outcome_now']} 経過={r['b2cls']} "
              f"AGENTS系={r['agentdoc_base']} CONTRIB={r['contrib_base']}")

print("\n== (3) CR から 180 日以内の更新(窓が完了した件 / 全件)")
print(f"{'cat':7} {'窓完了n':>6} {'AGENTS系更新':>13} {'うち新規作成':>11} {'CONTRIB更新':>12} {'いずれか更新':>12} {'関連内容追加(kw≥2)':>18} {'厳格(並べ替え95%超)':>16}")
def line3(lab, ss):
    o = [r for r in ss if r["ok"] and r["window_complete"]]
    print(f"{lab:7} {len(o):>6} {pct(sum(r['upd_agentdoc'] for r in o), len(o)):>13} {sum(r['new_agentdoc'] for r in o):>11} "
          f"{pct(sum(r['upd_contrib'] for r in o), len(o)):>12} {pct(sum(r['upd_any'] for r in o), len(o)):>12} {pct(sum(r['related_added'] for r in o), len(o)):>18} {pct(sum(r['related_strict'] for r in o), len(o)):>16}"
          f"   | 全件(窓途中含む) n={sum(r['ok'] for r in ss)} 更新 {sum(bool(r['upd_any']) for r in ss)} 関連 {sum(bool(r['related_added']) for r in ss)}")
for c in CATS:
    line3(c, [r for r in rows if key(r) == c])
for lab, gs in (("K計", "K"), ("R計", "R"), ("D計", "D")):
    line3(lab, [r for r in rows if r["g"] == gs])
line3("全体", rows)

# 並べ替え基準: 他件のキーワードを当てたときの陽性率(更新のあった件に限る)
U = [r for r in rows if r["ok"] and r["upd_any"]]
pos = []
for r in U:
    dl = diffs(r["sid"])
    for o in rows:
        if o["sid"] != r["sid"] and o["repo"] != r["repo"]:
            pos.append(len(hits(kw(o["sid"]), dl)) >= 2)
print(f"\n並べ替え基準(更新のあった {len(U)} 件の差分に他 repo の件のキーワードを当てた陽性率): {np.mean(pos):.3f}(n={len(pos)})")
print(f"実際の陽性率(更新のあった件): {np.mean([r['related_added'] for r in U]):.3f}(n={len(U)})")
print("\n== 関連内容追加と判定された件(キーワード)")
for r in rows:
    if r["related_added"]:
        print(f" {'厳格' if r['related_strict'] else '    '} {r['sid']} {r['repo']} {r['v1']} 窓完了={r['window_complete']} kw={r['kw_hit_words']}")
print("\n== 更新があった件の一覧(cat, 更新コミット数, ヒット語)")
for r in sorted(U, key=lambda r: key(r)):
    print(f" {key(r):7} {r['sid']} {r['repo']:45} commits={r['n_upd_commits']:>3} 新規AGENTS系={r['new_agentdoc']} hits={r['kw_hits']} [{r['kw_hit_words'][:80]}]")
