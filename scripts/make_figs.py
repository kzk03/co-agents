"""HUMANS-md調査 図の生成。実行(humans_md/ で): uv run scripts/make_figs.py
出力: outputs/fig/ と Vault の HUMANS-md調査/fig/ (ノート埋め込み用)"""
import collections, csv, json, os, shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GR = os.path.join(ROOT, "outputs", "gerrit")
OUT = os.path.join(ROOT, "outputs", "fig")
VAULT_FIG = "/Users/kazuki-h/Library/Mobile Documents/iCloud~md~obsidian/Documents/obsidian_brain/Research/HUMANS-md/fig"
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": "Hiragino Sans", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#8a8984", "axes.labelcolor": "#52514e",
    "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6,
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
})
INK, INK2 = "#0b0b0b", "#52514e"
C_COL, H_COL, M_COL = "#2a78d6", "#eb6834", "#a3a29c"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"

smp = {r["sid"]: r for r in json.load(open(os.path.join(GR, "gerrit_pilot_sample100.json")))}
irr = {r["sid"]: r for r in csv.DictReader(open(os.path.join(GR, "irr", "irr_merged.csv")))}
NAMES = {"C1": "C1 正しさ・不完全", "C2": "C2 保守性・スタイル", "C3": "C3 テスト/リリースノート不足",
         "M": "M CI失敗・競合", "H1": "H1 人間の文脈(合意・他パッチ)", "H2": "H2 方針・設計判断",
         "H3": "H3 暗黙の前提(運用・環境)", "H4": "H4 プロセス・責任", "H5": "H5 セキュリティ・権限"}
grp = lambda c: "H" if c.startswith("H") else ("C" if c[0] in "CM" else None)


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=200, bbox_inches="tight")
    plt.close(fig)


# 図1 理由の内訳(3コーダー多数決)
valid = [s for s in irr if irr[s]["majority"] in NAMES]
cnt = collections.Counter(irr[s]["majority"] for s in valid)
order = ["H1", "H2", "H3", "H4", "H5", "C1", "C2", "C3", "M"][::-1]
fig, ax = plt.subplots(figsize=(7, 4))
cols = [H_COL if k.startswith("H") else (M_COL if k == "M" else C_COL) for k in order]
ax.barh([NAMES[k] for k in order], [cnt[k] for k in order], color=cols, height=0.62)
for i, k in enumerate(order):
    ax.text(cnt[k] + 0.3, i, str(cnt[k]), va="center", color=INK2, fontsize=9)
ax.set_xlabel("件数(多数決ラベル, n=%d)" % len(valid))
ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
ax.grid(axis="y", visible=False)
h = sum(cnt[k] for k in cnt if k.startswith("H"))
ax.set_title("レビューで止めた理由:H系(人間の文脈・判断)が %d/%d 件\n全体補正後の推定 約40%%(95%%区間 28–52%%)" % (h, len(valid)),
             loc="left", color=INK, fontsize=11)
save(fig, "fig1_理由の内訳.png")

# 図2 投票の強さ・結末ごとの C/H 比率
def share(filter_fn):
    ss = [s for s in valid if filter_fn(smp[s])]
    c = collections.Counter("M" if irr[s]["majority"] == "M" else grp(irr[s]["majority"]) for s in ss)
    n = len(ss)
    return n, c["C"] / n, c["H"] / n, c["M"] / n

groups = [("-1", lambda r: r["vote"] == -1), ("-2", lambda r: r["vote"] == -2),
          ("マージ", lambda r: r["status"] == "MERGED"), ("放棄", lambda r: r["status"] == "ABANDONED"),
          ("審査中", lambda r: r["status"] == "NEW")]
fig, ax = plt.subplots(figsize=(7, 3.4))
labels = []
for i, (lab, fn) in enumerate(groups):
    n, c, hh, m = share(fn)
    labels.append(f"{lab}\n(n={n})")
    ax.barh(i, hh, color=H_COL, height=0.6, edgecolor="#fcfcfb", linewidth=2, label="H系" if i == 0 else None)
    ax.barh(i, c, left=hh, color=C_COL, height=0.6, edgecolor="#fcfcfb", linewidth=2, label="C系" if i == 0 else None)
    ax.barh(i, m, left=hh + c, color=M_COL, height=0.6, edgecolor="#fcfcfb", linewidth=2, label="M" if i == 0 else None)
    ax.text(hh / 2, i, f"{hh:.0%}", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
ax.set_yticks(range(len(groups)), labels)
ax.invert_yaxis()
ax.set_xlim(0, 1)
ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
ax.axhline(1.5, color="#c3c2b7", linewidth=0.8)
ax.grid(axis="y", visible=False)
ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False)
ax.set_title("強い拒否(-2)と放棄された変更ほど H 系が多い", loc="left", color=INK, fontsize=11, pad=24)
save(fig, "fig2_投票と結末別.png")

# 図3 コーダー間一致(κ)
kap = {"C系/H系の二分": (0.83, 0.75, 0.73), "11カテゴリ": (0.71, 0.63, 0.64), "コードから分かるか": (0.59, 0.57, 0.48)}
fig, ax = plt.subplots(figsize=(7, 3.4))
w = 0.26
for j, (pair, col) in enumerate(zip(["Opus–Sonnet", "Opus–Haiku", "Sonnet–Haiku"], [S1, S2, S3])):
    xs = [i + (j - 1) * w for i in range(3)]
    vals = [v[j] for v in kap.values()]
    ax.bar(xs, vals, width=w - 0.03, color=col, label=pair)
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.015, f"{v:.2f}", ha="center", color=INK2, fontsize=8)
ax.set_xticks(range(3), list(kap))
ax.set_ylim(0, 1)
for y, t in [(0.6, "かなりの一致 0.6"), (0.8, "ほぼ完全 0.8")]:
    ax.axhline(y, color="#8a8984", linewidth=0.8, linestyle="--")
    ax.text(2.62, y, t, ha="left", va="center", color=INK2, fontsize=8)
ax.set_ylabel("Cohen の κ")
ax.grid(axis="x", visible=False)
ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0))
ax.set_title("C/H の二分は再現できるが、「コードから分かるか」の判定は揺れる", loc="left", color=INK, fontsize=11, pad=24)
save(fig, "fig3_コーダー間一致.png")

# 図4 判断の集中(ローレンツ曲線)
allv = [r for r in json.load(open(os.path.join(GR, "gerrit_neg_votes_all.json"))) if not r["is_self"]]
fig, ax = plt.subplots(figsize=(5.2, 4.6))
for lab, rows, col in [("-1/-2 全体(30,269票・958人)", allv, S1),
                       ("-2 のみ(909票・141人)", [r for r in allv if r["vote"] == -2], S2)]:
    v = sorted(collections.Counter(r["reviewer"] for r in rows).values(), reverse=True)
    t, n, acc, xs, ys = sum(v), len(v), 0, [0], [0]
    for i, x in enumerate(v, 1):
        acc += x; xs.append(i / n); ys.append(acc / t)
    ax.plot(xs, ys, color=col, linewidth=2, label=lab)
ax.plot([0, 1], [0, 1], color="#c3c2b7", linewidth=1, linestyle="--")
ax.axvline(0.1, color="#8a8984", linewidth=0.8)
ax.annotate("上位10%で79%", (0.1, 0.79), (0.25, 0.62), color=INK2, fontsize=9,
            arrowprops=dict(arrowstyle="-", color="#8a8984"))
ax.annotate("上位10%で53%", (0.1, 0.53), (0.25, 0.4), color=INK2, fontsize=9,
            arrowprops=dict(arrowstyle="-", color="#8a8984"))
ax.set_xlabel("レビュアー(票数の多い順)の累積割合")
ax.set_ylabel("投票の累積割合")
for f in (ax.xaxis, ax.yaxis):
    f.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
ax.legend(frameon=False, loc="lower right", fontsize=9)
ax.set_title("止める判断は一部のレビュアーに集中している", loc="left", color=INK, fontsize=11)
save(fig, "fig4_判断の集中.png")

# 図5 HUMANS.md の実態(件数の絞り込み)
steps = [("code search の\nヒット(概数)", 2560), ("取得した\n上位1000件", 1000), ("ファイル名が\n完全一致", 186),
         ("AI関連の語を含む", 48), ("「人間が判断すべきこと」\nを書いた型(目安)", 5)]
fig, ax = plt.subplots(figsize=(7, 3.2))
ax.barh(range(len(steps)), [s[1] for s in steps], color=[C_COL] * 4 + [H_COL], height=0.6)
for i, (_, v) in enumerate(steps):
    ax.text(v + 30, i, f"{v:,}", va="center", color=INK2, fontsize=9)
ax.set_yticks(range(len(steps)), [s[0] for s in steps])
ax.invert_yaxis()
ax.grid(axis="y", visible=False)
ax.set_xlabel("件数(参考:AGENTS.md は約119万件)")
ax.set_title("HUMANS.md はほぼ普及しておらず、「判断」を書いた型はごく一部", loc="left", color=INK, fontsize=11)
save(fig, "fig5_HUMANSmd実態.png")
for f in os.listdir(OUT):
    shutil.copy(os.path.join(OUT, f), VAULT_FIG)
print("ok", os.listdir(OUT))

# 図6 Gerrit(人間同士) vs GitHub(エージェント PR)の理由の構成(多数決ラベル)
def comp(path):
    m = [r["majority"] for r in csv.DictReader(open(path)) if r["majority"] in NAMES]
    c = collections.Counter(m); n = len(m)
    return n, {k: c[k] / n for k in NAMES}

sets = [("Gerrit OpenStack\n人間同士(-1/-2)", os.path.join(GR, "irr", "irr_merged.csv")),
        ("GitHub AIDev\nエージェントPR(CR)", os.path.join(ROOT, "outputs", "aidev", "irr", "irr_merged.csv"))]
H_SHADES = {"H1": "#c2410c", "H2": "#eb6834", "H3": "#f08a5d", "H4": "#f5ab88", "H5": "#f9ccb4"}
C_SHADES = {"C1": "#1d5fa8", "C2": "#2a78d6", "C3": "#73a6e6", "M": "#a3a29c"}
fig, ax = plt.subplots(figsize=(7.5, 3.2))
labels = []
for i, (lab, p) in enumerate(sets):
    n, sh = comp(p); labels.append(f"{lab}\n(n={n})"); left = 0
    for k, col in list(H_SHADES.items()) + list(C_SHADES.items()):
        ax.barh(i, sh[k], left=left, color=col, height=0.6, edgecolor="#fcfcfb", linewidth=1.5,
                label=NAMES[k] if i == 0 else None)
        if sh[k] >= 0.06:
            ax.text(left + sh[k] / 2, i, k, ha="center", va="center", color="white", fontsize=8, fontweight="bold")
        left += sh[k]
    h = sum(sh[k] for k in H_SHADES)
    ax.text(1.01, i, f"H系 {h:.0%}", va="center", color=INK2, fontsize=9)
ax.set_yticks(range(len(sets)), labels); ax.invert_yaxis(); ax.set_xlim(0, 1)
ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1)); ax.grid(axis="y", visible=False)
ax.legend(ncol=3, fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.18))
ax.set_title("エージェント PR では、人間の止め方はほぼコードレベルの指摘(サンプル内の構成比)", loc="left", color=INK, fontsize=11)
save(fig, "fig6_Gerrit対GitHub.png")
for f in os.listdir(OUT):
    shutil.copy(os.path.join(OUT, f), VAULT_FIG)
