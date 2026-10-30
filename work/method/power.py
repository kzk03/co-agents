# 検出力計算(α=0.05 両側、検出力0.8)。仮定値は REPORT に明記
import numpy as np
from statsmodels.stats.power import NormalIndPower, TTestIndPower
from statsmodels.stats.proportion import proportion_effectsize
from scipy.stats import norm
za, zb = norm.ppf(0.975), norm.ppf(0.8)
P = NormalIndPower()
def n2(p1,p2): return int(np.ceil(P.solve_power(proportion_effectsize(p1,p2),alpha=0.05,power=0.8)))
print("== 2群の比率差(各群n)")
for p1,p2 in [(0.29,0.64),(0.30,0.60),(0.35,0.60),(0.40,0.60),(0.45,0.60),(0.33,0.55)]:
    print(f" {p1:.2f} vs {p2:.2f}: n/群={n2(p1,p2)}")
print("== McNemar(同じ項目を旧/新モデルで、対応あり)。不一致率 pd、不一致内の比 改善:悪化")
def mcn(pdisc, ratio):
    # Connor 1987 近似
    p10 = pdisc*ratio/(1+ratio); p01 = pdisc/(1+ratio); d = p10-p01
    n = (za*np.sqrt(pdisc)+zb*np.sqrt(pdisc-d**2))**2/d**2
    return int(np.ceil(n))
for pdisc,ratio in [(0.30,3),(0.25,3),(0.20,3),(0.30,2),(0.20,2)]:
    print(f" 不一致率{pdisc} 改善:悪化={ratio}:1 → n項目={mcn(pdisc,ratio)}")
print("== 世代×群の交互作用(傾きの差)。ロジスティック、世代G=4点(0..3)、項目ランダム効果は設計効果で近似")
# シミュレーション:群H/C各n、世代4、 logit p = a + b*g + c*H + d*g*H + u_i, u~N(0,s)
import statsmodels.api as sm
rng = np.random.default_rng(1)
def sim(n, b=0.5, d=-0.5, a=0.0, c=-0.5, s=1.0, G=4, R=300):
    hits=0
    for _ in range(R):
        H = np.repeat([0,1], n); u = rng.normal(0,s,2*n)
        rows=[]
        g = np.tile(np.arange(G), 2*n); Hi = np.repeat(H, G); ui = np.repeat(u, G); idx=np.repeat(np.arange(2*n),G)
        eta = a + b*g + c*Hi + d*g*Hi + ui
        y = rng.random(len(eta)) < 1/(1+np.exp(-eta))
        X = sm.add_constant(np.column_stack([g,Hi,g*Hi]))
        try:
            m = sm.GLM(y.astype(float), X, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": idx})
            hits += m.pvalues[3] < 0.05
        except Exception: pass
    return hits/R
for n in [40,60,80,120]:
    print(f" 各群n={n}: 交互作用 d=-0.5(Hの傾きがCの0) 検出力={sim(n):.2f}; d=-0.35 検出力={sim(n,b=0.35,d=-0.35):.2f}")
print("== κ の精度(期待κ=0.6, po=0.8 程度, pe=0.5):95%CI 半幅 h に必要 n  [SE≈sqrt(po(1-po)/(n(1-pe)^2))]")
for h in [0.15,0.10,0.08]:
    po,pe=0.8,0.5; n=(1.96**2)*po*(1-po)/((1-pe)**2*h**2); print(f" 半幅{h}: n={int(np.ceil(n))}")
print("== 単一比率の精度(半幅)")
for p,h in [(0.2,0.05),(0.3,0.05),(0.3,0.07),(0.5,0.10)]:
    print(f" p={p} 半幅{h}: n={int(np.ceil(1.96**2*p*(1-p)/h**2))}")
print("== 感度・特異度(LLM判定 vs 人間)の精度、半幅0.10, 期待0.8: n陽性=",int(np.ceil(1.96**2*0.8*0.2/0.01)))
print("== DiD(repo単位、2期)。結果=repo 期ごとの比率。repo間SD σ、期間相関ρ。MDE=2.8*σ*sqrt(2(1-ρ))*sqrt(1/Nt+1/Nc)")
for Nt,Nc in [(30,30),(60,60),(100,100),(200,200)]:
    for sig,rho in [(0.15,0.5)]:
        mde=2.8*sig*np.sqrt(2*(1-rho))*np.sqrt(1/Nt+1/Nc)
        print(f" 処置{Nt} 対照{Nc} σ={sig} ρ={rho}: MDE={mde:.3f}")
print("== 介入イベント:理由なし率 p≈0.33(Peralta) を半幅0.05 で:", int(np.ceil(1.96**2*0.33*0.67/0.05**2)))
from statsmodels.stats.proportion import proportion_confint
print("== 追加")
print(" Wilson 14/15:", [round(x,3) for x in proportion_confint(14,15,method='wilson')])
print(" 0.40 vs 0.50 n/群:", n2(0.40,0.50), " 0.35 vs 0.45:", n2(0.35,0.45))
p=0.4; m=0.10; print(" 同等性 TOST(p=0.4、真の差0、マージン±0.10、検出力0.8)n/群:", int(np.ceil((norm.ppf(0.95)+norm.ppf(0.9))**2*2*p*(1-p)/m**2)))
po,pe=0.8,0.5; print(" κ半幅 n=50:", round(1.96*np.sqrt(po*(1-po)/(50*(1-pe)**2)),3))
