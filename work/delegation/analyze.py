"""Aggregate delegation results. Output: analysis.txt, upstream_merged.csv"""
import json, os, glob, math, collections
import pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__))
P = []
def out(*a):
    s = " ".join(str(x) for x in a); print(s); P.append(s)
def wilson(k, n, z=1.96):
    if n == 0: return (float("nan"),) * 2
    p = k / n; d = 1 + z*z/n; c = p + z*z/(2*n); h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return ((c-h)/d, (c+h)/d)
def fisher(a, b, c, d):  # two-sided
    n = a+b+c+d; r1 = a+b; c1 = a+c
    pr = lambda x: math.comb(r1, x)*math.comb(n-r1, c1-x)/math.comb(n, c1)
    p0 = pr(a); return min(1, sum(pr(x) for x in range(max(0, c1-(n-r1)), min(r1, c1)+1) if pr(x) <= p0*(1+1e-9)))
def kappa(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b))/n
    ca, cb = collections.Counter(a), collections.Counter(b); pe = sum(ca[k]*cb[k] for k in set(a)|set(b))/n/n
    return po, (po-pe)/(1-pe) if pe < 1 else float("nan")

# ---- 1. existing table
t = pd.read_csv(os.path.join(BASE, "delegation_table.csv"))
t["grp"] = t.majority.map(lambda c: "H" if str(c).startswith("H") else ("C" if c in ("C1","C2","C3","M") else "other"))
out("== 1. delegation_table.csv (aidev sample100) ==")
out("PR取得可:", int(t.available.sum()), "/ 100")
out("依頼者特定:", int(t.requester.notna().sum()), "/ 100;", t.requester_src.value_counts(dropna=False).to_dict())
k = int((t.reviewer_is_requester == True).sum()); n = int(t.reviewer_is_requester.notna().sum())
out(f"レビュアー=依頼者: {k}/{n} = {k/n:.1%} (95%CI {wilson(k,n)[0]:.1%}-{wilson(k,n)[1]:.1%}); 100件分母では {k}%")
out("レビュアーがCopilotを起動した本人(copilot_work_started):", int(t.reviewer_drove_agent.sum()), "/ 100")
ka = int((t.reviewer_is_issue_author == True).sum()); na = int(t.reviewer_is_issue_author.notna().sum())
out(f"レビュアー=Issue作成者(Issueあり{na}件中): {ka} = {ka/na:.1%}")
for c in ["agent", "grp", "stratum"]:
    g = t.groupby(c).agg(n=("sid","size"), rr=("reviewer_is_requester", lambda s: f"{int((s==True).sum())}/{int(s.notna().sum())}"))
    out(f"-- レビュアー=依頼者 by {c}:", g.to_dict("index"))

# ---- 2. upstream judgments
me = pd.read_csv(os.path.join(BASE, "upstream_me.csv"))
so = {}
for f in sorted(glob.glob(os.path.join(BASE, "sonnet", "*.jsonl"))):
    for l in open(f):
        if l.strip().startswith("{"):
            try: j = json.loads(l); so[j["sid"]] = j
            except json.JSONDecodeError: pass
me["sonnet"] = me.sid.map(lambda s: so.get(s, {}).get("up"))
me["sonnet_dec"] = me.sid.map(lambda s: so.get(s, {}).get("dec"))
me["sonnet_req_quote"] = me.sid.map(lambda s: so.get(s, {}).get("req_quote"))
auto = (me.side == "human") & (me.req_src != "issue")
me.loc[auto, "sonnet"] = "U4"; me.loc[auto, "sonnet_dec"] = "NA"
me["strict"] = me.req_src.isin(["issue", "pr_body:Original prompt"])
me.to_csv(os.path.join(BASE, "upstream_merged.csv"), index=False)
out("\n== 2. 上流判定: 自分 vs sonnet ==")
for side in ["agent", "human"]:
    d = me[(me.side == side) & ~( (me.side=="human") & auto )]
    d = d[d.sonnet.notna()]
    po, kp = kappa(list(d.me), list(d.sonnet))
    out(f"[{side}] 判定対象 n={len(d)} 4値 一致率={po:.2f} κ={kp:.2f}")
    out("  混同行列(行=自分,列=sonnet):\n" + pd.crosstab(d.me, d.sonnet).to_string())
    b = d[(d.me != "U4") & (d.sonnet != "U4")]
    up = lambda x: "UP" if x in ("U1","U2") else "NEW"
    po, kp = kappa([up(x) for x in b.me], [up(x) for x in b.sonnet])
    out(f"  両者U4以外 n={len(b)} 上流(U1+U2)/初出(U3) 二値 一致率={po:.2f} κ={kp:.2f}")
    dd = d[d.me_dec.isin(["Y","N"]) & d.sonnet_dec.isin(["Y","N"])]
    po, kp = kappa(list(dd.me_dec), list(dd.sonnet_dec))
    out(f"  dec(依頼文に判断が書かれているか) n={len(dd)} 一致率={po:.2f} κ={kp:.2f}")
missing = me[(me.sonnet.isna())].sid.tolist(); out("sonnet出力欠落:", missing)

# ---- 3. distributions
def dist(d, col):
    c = d[col].value_counts().reindex(["U1","U2","U3","U4"], fill_value=0); j = d[d[col] != "U4"]
    kup = int(j[col].isin(["U1","U2"]).sum()); lo, hi = wilson(kup, len(j))
    return f"n={len(d)} U1={c.U1} U2={c.U2} U3={c.U3} U4={c.U4} | 判定可{len(j)}中 上流={kup} ({kup/len(j) if len(j) else float('nan'):.1%}, CI {lo:.1%}-{hi:.1%})"
for coder in ["me", "sonnet"]:
    out(f"\n== 3. 分布 (coder={coder}) ==")
    for side in ["agent", "human"]:
        d = me[me.side == side]
        out(f"[{side}] 全体: " + dist(d, coder))
        out(f"[{side}] strict依頼文(Issue/原プロンプト)のみ: " + dist(d[d.strict], coder))
        for g in ["H", "C", "other"]:
            out(f"[{side}] group={g}: " + dist(d[d.group == g], coder))
        out(f"[{side}] strict & group=H: " + dist(d[d.strict & (d.group=="H")], coder))
        out(f"[{side}] strict & group=C: " + dist(d[d.strict & (d.group=="C")], coder))
    a = me[me.side == "agent"]
    for ag, d in a.groupby("agent"): out(f"[agent] agent={ag}: " + dist(d, coder))
    for v, d in a.groupby(a.reviewer_is_requester.astype(str)): out(f"[agent] reviewer_is_requester={v}: " + dist(d, coder))
    for v, d in a.groupby(a.req_src): out(f"[agent] req_src={v}: " + dist(d, coder))
    # agent vs human (strict, judgable)
    def cnt(d):
        j = d[d.strict & (d[coder] != "U4")]; return int(j[coder].isin(["U1","U2"]).sum()), len(j)
    ka_, na_ = cnt(me[me.side=="agent"]); kh_, nh_ = cnt(me[me.side=="human"])
    out(f"エージェント vs 人間(strict依頼文・判定可): 上流 {ka_}/{na_} vs {kh_}/{nh_}, Fisher p={fisher(ka_, na_-ka_, kh_, nh_-kh_):.3f}")
    for g in ["H","C"]:
        ka_, na_ = cnt(me[(me.side=="agent")&(me.group==g)]); kh_, nh_ = cnt(me[(me.side=="human")&(me.group==g)])
        out(f"  group={g}: {ka_}/{na_} vs {kh_}/{nh_}, Fisher p={fisher(ka_, na_-ka_, kh_, nh_-kh_):.3f}")

# ---- 4. request availability & decisions
out("\n== 4. 依頼文の有無と中身 ==")
for side in ["agent","human"]:
    d = me[me.side == side]
    out(f"[{side}] req_src:", d.req_src.value_counts().to_dict())
    for g in ["H","C"]:
        dg = d[d.group == g]; out(f"  group={g}: strict依頼文あり {int(dg.strict.sum())}/{len(dg)}")
    for coder, col in [("me","me_dec"),("sonnet","sonnet_dec")]:
        x = d[d[col].isin(["Y","N"])]; ky = int((x[col]=="Y").sum())
        out(f"  dec({coder}): Y={ky}/{len(x)} ({ky/len(x):.0%})" if len(x) else "")
ka = me[(me.side=="agent")&me.me_dec.isin(["Y","N"])]; kh = me[(me.side=="human")&me.me_dec.isin(["Y","N"])]
a1 = int((ka.me_dec=="Y").sum()); h1 = int((kh.me_dec=="Y").sum())
out(f"dec(me) agent {a1}/{len(ka)} vs human {h1}/{len(kh)} Fisher p={fisher(a1,len(ka)-a1,h1,len(kh)-h1):.3f}")
# human: reviewer = issue author
h = me[(me.side=="human") & (me.req_src=="issue")]
out(f"[human] Issueあり{len(h)}件: レビュアー=Issue作成者 {int((h.reviewer==h.issue_author).sum())}")
open(os.path.join(BASE, "analysis.txt"), "w").write("\n".join(P) + "\n")
