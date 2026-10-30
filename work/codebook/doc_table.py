"""文書化可能性の集計(私のラベル + 文書確認)。uv run python work/codebook/doc_table.py"""
import collections, csv, glob, json, os
W = os.path.dirname(os.path.abspath(__file__))
m = {r["sid"]: r for r in csv.DictReader(open(os.path.join(W, "coding_merged_v1.csv")))}
# 私の文書確認(cache の文書を grep と通読で確認。work/codebook/REPORT.md 参照)
ME_WRITTEN = {"G094": "yes", "H024": "yes", "G027": "yes", "H052": "yes"}
ELSEWHERE = {"H004": "developers.home-assistant.io の entity model 変更手続き(レビュアーがリンク)",
             "G024": "repo の wiki FilterListViewUrl(レビュアーがリンク)"}
so = {}
for f in glob.glob(os.path.join(W, "doccheck/*.jsonl")):
    for l in open(f):
        if l.strip().startswith("{"):
            j = json.loads(l); so[j["sid"]] = j["written"]
cache = {s: json.load(open(os.path.join(W, "cache", f"{s}.json"))) for s in m}
def doc_status(s):
    if s in ME_WRITTEN: return "written-repo"
    if s in ELSEWHERE: return "written-elsewhere"
    if not cache[s]["docs"]: return "未確認(repo取得不可)"
    return {"could": "could", "no": "no"}.get(m[s]["me_doc"], "-")
rows = []
for s, r in m.items():
    rows.append(dict(set=r["set"], sid=s, me=r["me"], doc=doc_status(s), sonnet_written=so.get(s, "")))
with open(os.path.join(W, "doc_status.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
cats = ["K-pub", "K-priv", "R-tech", "R-gov", "D-dir", "D-risk"]
docs = ["written-repo", "written-elsewhere", "could", "no", "未確認(repo取得不可)"]
for name in ("aidev", "ghhuman", "all"):
    rs = [x for x in rows if name == "all" or x["set"] == name]
    ct = collections.Counter((x["me"], x["doc"]) for x in rs)
    print(f"== {name}(行=v1 me, 列=文書化) n={len(rs)}")
    print(f"{'':8}" + "".join(f"{d[:14]:>16}" for d in docs) + f"{'計':>6}")
    for c in cats:
        print(f"{c:8}" + "".join(f"{ct[(c, d)]:>16}" for d in docs) + f"{sum(ct[(c, d)] for d in docs):>6}")
    print(f"{'計':8}" + "".join(f"{sum(ct[(c, d)] for c in cats):>16}" for d in docs))
# 私 vs sonnet の written 判定一致
pairs = [(("yes" if x["sid"] in ME_WRITTEN else "no"), x["sonnet_written"]) for x in rows if x["sonnet_written"]]
print("written 判定 n", len(pairs), "完全一致", sum(a == b for a, b in pairs), "yes/非yes 一致", sum((a == "yes") == (b == "yes") for a, b in pairs))
print("sonnet written 分布", collections.Counter(b for _, b in pairs))
