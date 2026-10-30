"""LLM コーダーによる分類と一致率(κ)・全体推定。

使い方(humans_md/ で):
  python3 scripts/irr.py code <gerrit|aidev|ghhuman> <sonnet|haiku>   # claude -p で分類 → <dir>/irr/<model>_batch*.jsonl
  python3 scripts/irr.py stats <gerrit|aidev|ghhuman>               # κ・分布・重み付き推定 → <dir>/irr/irr_merged.csv

LLM にはコードブックとレビューテキストだけを渡す(差分・コードは渡さない、ツール使用不可)。
claude -p は CLAUDE.md を読み込まないよう、空の作業ディレクトリ(<dir>/irr/_cwd)で実行する。
"""
import collections, csv, glob, json, os, random, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DENY = "Bash,Read,Write,Edit,WebFetch,WebSearch,Agent,Glob,Grep,TodoWrite,ToolSearch,Skill,NotebookEdit"
SETS = {
    "gerrit": dict(dir="outputs/gerrit", dump="pilot_dump.txt", me="pilot_coding_v0.csv",
                   book="codebook_v0.md", sample="gerrit_pilot_sample100.json", sid=r"S\d{3}"),
    "gerrit_blind": dict(dir="outputs/gerrit_blind", dump="pilot_dump.txt", me="pilot_coding_v0.csv",
                         book="codebook_v0.md", sample="gerrit_pilot_sample100.json", sid=r"S\d{3}"),
    "aidev": dict(dir="outputs/aidev", dump="dump.txt", me="coding_opus_v0.csv",
                  book="codebook_v0_github.md", sample="sample100.json", sid=r"G\d{3}"),
    # GitHub 人間作者 PR への人間 CR(pilot/raw_full 由来、work/baseline/extract.py・sample.py で作成)
    "ghhuman": dict(dir="outputs/ghhuman", dump="dump.txt", me="coding_opus_v0.csv",
                    book="codebook_v0_github_human.md", sample="sample100.json", sid=r"H\d{3}",
                    pop="work/baseline/ghhuman_blocks.jsonl"),
    # 同一 repo 内比較(work/baseline/within_sample.py で作成、群・結末は伏せたダンプ)。stats は work/baseline/within_stats.py を使う
    "within": dict(dir="work/baseline/within", dump="dump.txt", me="coding_opus_v0.csv",
                   book="codebook_v0_github_blind.md", sample="sample.json", sid=r"W\d{3}"),
}


def paths(name):
    s = dict(SETS[name]); s["dir"] = os.path.join(ROOT, s["dir"]); s["irr"] = os.path.join(s["dir"], "irr")
    return s


def make_batches(s, n=25):
    items = [i for i in re.split(rf"(?m)^(?=### {s['sid']})", open(os.path.join(s["dir"], s["dump"])).read()) if i.strip()]
    for b in range(0, len(items), n):
        open(os.path.join(s["irr"], f"batch{b // n}.txt"), "w").write("".join(items[b:b + n]))


def code(name, model):
    s = paths(name); make_batches(s)
    cwd = os.path.join(s["irr"], "_cwd"); os.makedirs(cwd, exist_ok=True)
    book = open(os.path.join(s["irr"], s["book"])).read()
    procs = []
    for f in sorted(glob.glob(os.path.join(s["irr"], "batch*.txt"))):
        out = open(f.replace("batch", f"{model}_batch").replace(".txt", ".jsonl"), "w")
        p = subprocess.Popen(["claude", "-p", "--model", model, "--max-turns", "1", "--disallowedTools", DENY],
                             stdin=subprocess.PIPE, stdout=out, stderr=subprocess.DEVNULL, text=True, cwd=cwd)
        p.stdin.write(book + "\n\nITEMS:\n" + open(f).read()); p.stdin.close()
        procs.append(p)
    for p in procs:
        p.wait()


def load(s, model):
    d = {}
    for f in sorted(glob.glob(os.path.join(s["irr"], f"{model}_batch*.jsonl"))):
        for l in open(f):
            if l.strip().startswith("{"):
                try:
                    j = json.loads(l); d[j["sid"]] = j
                except json.JSONDecodeError:
                    pass
    return d


def kappa(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = collections.Counter(a), collections.Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / n / n
    return po, (po - pe) / (1 - pe)


def fleiss(rows):
    cats = sorted({c for r in rows for c in r}); N, n = len(rows), len(rows[0])
    P = [(sum(r.count(c) ** 2 for c in cats) - n) / (n * (n - 1)) for r in rows]
    pj = [sum(r.count(c) for r in rows) / (N * n) for c in cats]
    Pe = sum(p * p for p in pj)
    return (sum(P) / N - Pe) / (1 - Pe)


def strata(name, s):
    """層 → (母集団件数, sid→層)"""
    smp = {r["sid"]: r for r in json.load(open(os.path.join(s["dir"], s["sample"])))}
    if name in ("gerrit", "gerrit_blind"):
        allv = [r for r in json.load(open(os.path.join(s["dir"], "gerrit_neg_votes_all.json"))) if not r["is_self"]]
        era = lambda d: "early" if int(d[:4]) <= 2019 else ("mid" if int(d[:4]) <= 2022 else "late")
        pop = collections.Counter((r["vote"], era(r["date"])) for r in allv)
        return pop, {k: (r["vote"], era(r["date"])) for k, r in smp.items()}
    if name == "ghhuman":
        allv = [json.loads(l) for l in open(os.path.join(ROOT, s["pop"]))]
        pop = collections.Counter("closed" if r["outcome"] == "closed" else "not_closed"
                                  for r in allv if not r["agent_coauthor"])
        return pop, {k: r["stratum"] for k, r in smp.items()}
    import pandas as pd
    cr = pd.read_parquet(os.path.join(s["dir"], "human_blocks.parquet"))
    pop = collections.Counter("closed" if o == "closed" else "not_closed" for o in cr["outcome"])
    return pop, {k: r["stratum"] for k, r in smp.items()}


def stats(name):
    s = paths(name)
    me = {r["sid"]: r for r in csv.DictReader(open(os.path.join(s["dir"], s["me"])))}
    so, ha = load(s, "sonnet"), load(s, "haiku")
    sids = [k for k in me if k in so and k in ha]
    grp = lambda c: "H" if c.startswith("H") else ("C" if c[0] in "CM" else c)
    print("n", len(sids), "(sonnet", len(so), "haiku", len(ha), ")")
    for nm, f in [("cat", lambda x: x["cat"]), ("group", lambda x: grp(x["cat"])), ("inferable", lambda x: x["inferable"])]:
        A, B, C = ([f(d[k]) for k in sids] for d in (me, so, ha))
        print(nm, "opus-sonnet %.2f/%.2f" % kappa(A, B), "opus-haiku %.2f/%.2f" % kappa(A, C),
              "sonnet-haiku %.2f/%.2f" % kappa(B, C), "fleiss %.2f" % fleiss(list(zip(A, B, C))))
    maj, inf = {}, {}
    with open(os.path.join(s["irr"], "irr_merged.csv"), "w") as fo:
        w = csv.writer(fo)
        w.writerow(["sid", "me_cat", "sonnet_cat", "haiku_cat", "majority", "me_inf", "sonnet_inf", "haiku_inf", "majority_inf"])
        for k in sids:
            top = collections.Counter([me[k]["cat"], so[k]["cat"], ha[k]["cat"]]).most_common(1)[0]
            maj[k] = top[0] if top[1] >= 2 else "NOAGREE"
            ti = collections.Counter([me[k]["inferable"], so[k]["inferable"], ha[k]["inferable"]]).most_common(1)[0]
            inf[k] = ti[0] if ti[1] >= 2 else "NOAGREE"
            w.writerow([k, me[k]["cat"], so[k]["cat"], ha[k]["cat"], maj[k],
                        me[k]["inferable"], so[k]["inferable"], ha[k]["inferable"], inf[k]])
    for nm, d in [("opus", me), ("sonnet", so), ("haiku", ha)]:
        v = [k for k in sids if d[k]["cat"] not in ("BOT", "UNK")]
        h = sum(d[k]["cat"].startswith("H") for k in v); no = sum(d[k]["inferable"] == "no" for k in v)
        print(f"{nm}: valid={len(v)} H={h}({h / len(v):.0%}) no={no}({no / len(v):.0%})")
    pop, st = strata(name, s)
    scnt = collections.Counter(st[k] for k in sids)
    valid = [k for k in sids if maj[k] not in ("BOT", "UNK", "NOAGREE")]
    w = lambda k: pop[st[k]] / scnt[st[k]]

    def share(ss):
        return sum(w(k) for k in ss if maj[k].startswith("H")) / sum(w(k) for k in ss)

    random.seed(0)
    bs = sorted(share([random.choice(valid) for _ in valid]) for _ in range(2000))
    print("majority dist", dict(sorted(collections.Counter(maj.values()).items())))
    print("majority inferable", dict(collections.Counter(inf[k] for k in valid)))
    print("weighted H share %.3f (95%% CI %.3f-%.3f)" % (share(valid), bs[50], bs[1950]))
    for g in sorted(set(st.values()), key=str):
        ss = [k for k in valid if st[k] == g]
        print(" stratum", g, "n", len(ss), "H %.0f%%" % (100 * sum(maj[k].startswith("H") for k in ss) / len(ss)))


if __name__ == "__main__":
    {"code": lambda: code(sys.argv[2], sys.argv[3]), "stats": lambda: stats(sys.argv[2])}[sys.argv[1]]()
