"""分析4: 理由を書かない拒否の規模(AIDev-pop 全 PR)。
人間の活動 = PR 作成者以外の非ボットアカウントによる review / review comment / issue comment。
ボット判定 = user_type=='Bot' または login が '[bot]' で終わる / 'bot' を含む / 既知 CI 名(BOTS)。
Codex/Cursor/Claude_Code の PR は作成者が依頼者本人(人間)なので、作成者の発言は「人間の活動」に数えない。
uv run python work/explore/a4_silent.py"""
import os, re, collections
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
D = os.path.join(ROOT, "data/aidev")
BOTS = {"coveralls", "codecov", "netlify", "vercel", "sonarqubecloud", "sonarcloud", "changeset-bot", "cla-checker-service",
        "copilot", "codspeed-hq", "railway-app", "supabase", "gemini-code-assist", "coderabbitai", "sourcery-ai", "claude"}
def isbot(login, typ):
    l = str(login).lower()
    return typ == "Bot" or l.endswith("[bot]") or "bot" in l or l in BOTS
pr = pd.read_parquet(os.path.join(D, "pull_request.parquet"))
rv = pd.read_parquet(os.path.join(D, "pr_reviews.parquet"))
rc = pd.read_parquet(os.path.join(D, "pr_review_comments.parquet"))
ic = pd.read_parquet(os.path.join(D, "pr_comments.parquet"))
rc = rc.merge(rv[["id", "pr_id"]].rename(columns={"id": "pull_request_review_id"}), on="pull_request_review_id", how="left")
au = dict(zip(pr.id, pr.user.str.lower()))
act = pd.concat([rv[["pr_id", "user", "user_type"]], rc[["pr_id", "user", "user_type"]], ic[["pr_id", "user", "user_type"]]])
act = act[act.pr_id.notna()]
act["bot"] = [isbot(u, t) for u, t in zip(act.user, act.user_type)]
act["author"] = [str(u).lower() == au.get(p) for u, p in zip(act.user, act.pr_id)]
hum = set(act[~act.bot & ~act.author].pr_id)
humall = set(act[~act.bot].pr_id)
pr["human_act"] = pr.id.isin(hum); pr["human_any"] = pr.id.isin(humall)
pr["res"] = np.where(pr.merged_at.notna(), "merged", np.where(pr.state == "closed", "closed_unmerged", "open"))
out = []
def p(s): out.append(s); print(s)
p(f"AIDev-pop PR {len(pr)}  結末 {pr.res.value_counts().to_dict()}")
p("\n== 結末別:作成者以外の人間の活動(review/comment)が1つもない PR の割合")
for agent in ["(全体)"] + sorted(pr.agent.unique()):
    d = pr if agent == "(全体)" else pr[pr.agent == agent]
    row = []
    for r in ("closed_unmerged", "merged", "open"):
        x = d[d.res == r]
        row.append(f"{r} n={len(x)} 沈黙 {1 - x.human_act.mean():.3f}")
    p(f" {agent:13s} " + " | ".join(row))
cu = pr[pr.res == "closed_unmerged"]
p(f"\n閉じられた未マージ {len(cu)} のうち 作成者以外の人間の活動なし {(~cu.human_act).sum()} ({(~cu.human_act).mean():.3f})、ボット以外の活動が作成者含め一切なし {(~cu.human_any).sum()} ({(~cu.human_any).mean():.3f})")
crp = set(rv[(rv.state == "CHANGES_REQUESTED") & (rv.user_type == "User")].pr_id)
for agent in ["(全体)", "Copilot", "Devin", "OpenAI_Codex"]:
    d = cu if agent == "(全体)" else cu[cu.agent == agent]
    p(f" 未マージ close {agent}: n={len(d)} 人間 CR あり {d.id.isin(crp).mean():.3f} / 作成者以外の人間の活動あり {d.human_act.mean():.3f}")
# repo 集中
cs = cu[~cu.human_act]
vc = cs.repo_url.value_counts()
p(f" 沈黙クローズ {len(cs)} 件は {vc.size} repo。上位10 repo で {vc.head(10).sum()/len(cs):.3f}、上位1 repo {vc.index[0].split('/repos/')[1]} {vc.iloc[0]} 件")
p(" 上位10: " + ", ".join(f"{u.split('/repos/')[1]}({n})" for u, n in vc.head(10).items()))
# repo 単位の沈黙クローズ率(未マージ close >= 10 の repo)
g = cu.groupby("repo_url").human_act.agg(["size", "mean"])
g = g[g["size"] >= 10]
p(f" 未マージ close が10件以上の repo {len(g)} 個:沈黙率の repo 中央値 {1 - g['mean'].median():.3f}、四分位 {1 - g['mean'].quantile(.75):.3f}–{1 - g['mean'].quantile(.25):.3f}")
# 依頼者=作成者の agent(Codex 等)と Copilot/Devin/Jules に分ける
p("\n== 理由のない CR(既存 short_text.py と同定義:インラインなし かつ body<40字)をエージェント別に")
hb = pd.read_parquet(os.path.join(ROOT, "outputs/aidev/human_blocks.parquet"))
hb["short"] = (hb.n_inline == 0) & (hb.body.fillna("").str.strip().str.len() < 40)
REV = re.compile(r"^\s*(revert|no|nope|close|closing|not needed|do not|don't|won't|wont|nah)\b", re.I)
hb["revertlike"] = hb.body.fillna("").str.strip().map(lambda s: bool(REV.match(s)) and len(s) < 80)
for agent, d in [("(全体)", hb)] + list(hb.groupby("agent")):
    p(f" {agent:13s} CR n={len(d)} short {d.short.mean():.3f}  拒否語で始まる短文 {d.revertlike.mean():.3f}")
vc = hb[hb.short].html_url.str.extract(r"github.com/([^/]+/[^/]+)/")[0].value_counts()
p(f" short CR {hb.short.sum()} 件は {vc.size} repo、上位5 repo で {vc.head(5).sum()/hb.short.sum():.3f}: " + ", ".join(f"{u}({n})" for u, n in vc.head(5).items()))
p(" short CR の本文 上位:" + str(hb[hb.short].body.fillna("<空>").str.strip().str.lower().value_counts().head(12).to_dict()))
open(os.path.join(ROOT, "work/explore/a4_silent.out"), "w").write("\n".join(out) + "\n")
