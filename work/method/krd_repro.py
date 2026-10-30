# 既存出力の再集計のみ(LLM呼び出しなし): v1 カテゴリ別の再現率、文書化状況
import pandas as pd
p = pd.read_csv("work/reproduce/results/per_item_v1_aidev.csv")
c = pd.read_csv("work/codebook/coding_merged_v1.csv")
lk = pd.read_csv("work/reproduce/results/leakage_v1.csv")[["sid","dataset_body_eq_at_review"]]
d = pd.read_csv("work/codebook/doc_status.csv")
grp = lambda x: x if not isinstance(x,str) else (x.split("-")[0] if "-" in x else ("C" if x[0]=="C" or x=="M" else x))
m = p.merge(c[c.set=="aidev"][["sid","me","sonnet"]], on="sid", how="left").merge(lk, on="sid", how="left")
m["v1g"] = m.me.map(grp)
print("reproduce 30件の v1(me)群:", m.v1g.value_counts(dropna=False).to_dict())
print(pd.crosstab(m.grp, m.v1g))
for j in ["opus","sonnet"]:
  for cond in ["A","B","C"]:
    col=f"{j}_{cond}"
    t = m.groupby("v1g")[col].apply(lambda s: f"{(s=='yes').sum()}/{s.notna().sum()}")
    print(j,cond,"yes by v1g(全30):",t.to_dict())
    mm=m[m.dataset_body_eq_at_review==True]
    t = mm.groupby("v1g")[col].apply(lambda s: f"{(s=='yes').sum()}/{s.notna().sum()}")
    print(j,cond,"yes by v1g(リークなし18):",t.to_dict())
# opus リーク補正C
m["opus_Cfix"] = m.apply(lambda r: r.opus_Cr if isinstance(r.opus_Cr,str) else (r.opus_C if r.dataset_body_eq_at_review else None), axis=1)
print("opus 補正C yes by v1g:", m.groupby("v1g").opus_Cfix.apply(lambda s: f"{(s=='yes').sum()}/{s.notna().sum()}").to_dict())
print(m[["sid","grp","me","sonnet","dataset_body_eq_at_review","opus_A","opus_C","opus_Cr","sonnet_A","sonnet_C"]].to_string())
print("\n== codebook v1 全体(me)")
c["g_me"]=c.me.map(grp); c["g_s"]=c.sonnet.map(grp)
print(pd.crosstab(c.set, c.g_me, margins=True))
print(pd.crosstab(c.set, c.me))
hum = c.me.isin(["D-dir","D-risk","K-priv","R-gov"])
print("HUMANS固有(me):", c.groupby("set").apply(lambda g: f"{g.me.isin(['D-dir','D-risk','K-priv','R-gov']).sum()}/{len(g)}").to_dict())
print("\n== doc_status")
print(pd.crosstab(d.me, d.doc))
