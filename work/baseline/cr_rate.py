"""repo ごとの CR 使用率。
 - CR/PR = 人間レビュアーの CHANGES_REQUESTED 件数 / PR 数(理由テキストの有無を問わない)
 - CR付きPR率 = 人間 CR が1件以上ある PR / PR 数
 - CR/人間レビュー = 人間 CR / 人間レビュー全件(COMMENTED/APPROVED/CR/DISMISSED)
pilot(39 repo、AI レビューが付いた PR だけを集めた母集団):PR を作者種別で3つに分ける
   human = ボットでない作者、エージェント trailer なし / agent_strong = コーディングエージェント trailer あり /
   agent_weak = Copilot・Copilot Autofix・gemini-code-assist の trailer のみ
   レビュアー除外: ボット名、org 名アカウント、PR 作者本人(extract.py と同じ規則)
AIDev(エージェント作者 PR):pull_request × pr_reviews(user_type=User、ボット名除外)
実行(humans_md/ で): uv run work/baseline/cr_rate.py → work/baseline/cr_rate.txt, cr_rate_pilot.csv, cr_rate_aidev.csv
"""
import collections, glob, json, os, re
import pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/pilot_raw_full"))
BOTPAT = re.compile(r"bot\b|\[bot\]|-bot|bot-|^bot|copilot|devin|codex|cursor|claude|jules|dependabot|renovate|"
                    r"coderabbit|gemini|sourcery|ellipsis|greptile|qodo|sweep|openhands|github-actions|"
                    r"mergify|k8s-ci|codecov|sonarcloud|netlify|vercel|allcontributors|pre-commit-ci|"
                    r"roachdev-claude|paperclip|aider|amazon-q|chatgpt|openai|mintlify|graphite-app", re.I)
isbot = lambda l: (not l) or bool(BOTPAT.search(l))
ANY = re.compile(r"(?im)^co-authored-by:.*(copilot|claude|anthropic|cursor|codex|openai|devin|jules|"
                 r"gemini|paperclip|aider|openhands|sweep|amazon q|roachdev-claude)|generated with \[?claude code|🤖 generated with")
STRONG = re.compile(r"(?im)^co-authored-by:.*(claude|anthropic|cursor|codex|openai|devin|jules|paperclip|aider|openhands|"
                    r"amazon q|roachdev-claude)|generated with \[?claude code|🤖 generated with")
out = []; P = lambda *a: out.append(" ".join(str(x) for x in a))
rows = []
for d in sorted(glob.glob(RAW + "/*")):
    repo = os.path.basename(d).replace("__", "/", 1); owner = repo.split("/")[0]
    meta = {}
    for l in open(d + "/prs_full.jsonl"):
        try:
            j = json.loads(l)
        except json.JSONDecodeError:
            continue
        a = (j.get("author") or {}).get("login")
        msgs = "\n".join(c["commit"]["message"] or "" for c in ((j.get("commits") or {}).get("nodes") or []))
        kind = "bot" if isbot(a) else ("agent_strong" if STRONG.search(msgs) else ("agent_weak" if ANY.search(msgs) else "human"))
        meta[j["number"]] = (a, kind)
    agg = collections.defaultdict(collections.Counter)
    seen = set()
    for l in open(d + "/review_bodies.jsonl"):
        j = json.loads(l)
        if j["number"] in seen or j["number"] not in meta:
            continue
        seen.add(j["number"]); a, kind = meta[j["number"]]
        if kind == "bot":
            continue
        c = agg[kind]; c["pr"] += 1; ncr = 0
        for r in j["reviews"]:
            rv = r.get("author")
            if isbot(rv) or rv == owner or rv == a:
                continue
            c["rev"] += 1
            if r["state"] == "CHANGES_REQUESTED":
                ncr += 1
        c["cr"] += ncr; c["pr_with_cr"] += ncr > 0
    for kind, c in agg.items():
        rows.append(dict(repo=repo, kind=kind, **c))
pl = pd.DataFrame(rows).fillna(0)
for c in ["pr", "rev", "cr", "pr_with_cr"]:
    pl[c] = pl[c].astype(int)
pl["cr_per_pr"] = pl.cr / pl.pr; pl["pr_with_cr_rate"] = pl.pr_with_cr / pl.pr; pl["cr_per_rev"] = pl.cr / pl.rev.where(pl.rev > 0)
pl.sort_values(["kind", "pr"], ascending=[True, False]).to_csv(f"{ROOT}/work/baseline/cr_rate_pilot.csv", index=False, float_format="%.4f")
P("== pilot 合計(作者種別)")
for kind, x in pl.groupby("kind"):
    P(f" {kind}: repo {len(x)} PR {x.pr.sum()} 人間レビュー {x.rev.sum()} 人間CR {x.cr.sum()} CR付きPR {x.pr_with_cr.sum()}"
      f" | CR/PR {x.cr.sum() / x.pr.sum():.3f} CR付きPR率 {x.pr_with_cr.sum() / x.pr.sum():.3f} CR/人間レビュー {x.cr.sum() / x.rev.sum():.3f}")
h = pl[pl.kind == "human"].set_index("repo")
P("\n== pilot 人間作者 PR の repo 別(PR 数順)  PR / 人間CR / CR/PR / CR付きPR率 / CR/人間レビュー")
for r, x in h.sort_values("pr", ascending=False).iterrows():
    P(f"  {r}: {x.pr} / {x.cr} / {x.cr_per_pr:.3f} / {x.pr_with_cr_rate:.3f} / {x.cr_per_rev:.3f}")
hh = h[h.pr >= 100].cr_per_pr
P(f" repo 別 CR/PR(PR>=100 の {len(hh)} repo): 中央値 {hh.median():.3f} 最小 {hh.min():.3f} 最大 {hh.max():.3f}")
P(f" home-assistant/core を除く合計 CR/PR {h.drop('home-assistant/core').cr.sum() / h.drop('home-assistant/core').pr.sum():.3f}")

P("\n== pilot 同一 repo 内: 人間 PR vs エージェント(strong)PR の CR/PR(strong PR が 20 件以上の repo)")
s = pl[pl.kind == "agent_strong"].set_index("repo")
for r in s[s.pr >= 20].sort_values("pr", ascending=False).index:
    P(f"  {r}: human PR {h.loc[r].pr} CR/PR {h.loc[r].cr_per_pr:.3f} CR付き {h.loc[r].pr_with_cr_rate:.3f} | "
      f"agent_strong PR {s.loc[r].pr} CR/PR {s.loc[r].cr_per_pr:.3f} CR付き {s.loc[r].pr_with_cr_rate:.3f}")

pr = pd.read_parquet(f"{ROOT}/data/aidev/pull_request.parquet")
pr["repo"] = pr["html_url"].str.split("github.com/").str[1].str.split("/pull/").str[0]
rv = pd.read_parquet(f"{ROOT}/data/aidev/pr_reviews.parquet")
rv = rv[(rv.user_type == "User") & ~rv.user.fillna("").map(isbot)].merge(pr[["id", "repo"]].rename(columns={"id": "pr_id"}), on="pr_id")
g = pr.groupby("repo").size().rename("pr").to_frame()
g["rev"] = rv.groupby("repo").size(); g["cr"] = rv[rv.state == "CHANGES_REQUESTED"].groupby("repo").size()
g["pr_with_cr"] = rv[rv.state == "CHANGES_REQUESTED"].groupby("repo").pr_id.nunique()
g = g.fillna(0).astype(int); g["cr_per_pr"] = g.cr / g.pr; g["pr_with_cr_rate"] = g.pr_with_cr / g.pr
g.sort_values("pr", ascending=False).to_csv(f"{ROOT}/work/baseline/cr_rate_aidev.csv", float_format="%.4f")
P(f"\n== AIDev(エージェント作者 PR)合計: repo {len(g)} PR {g.pr.sum()} 人間レビュー {g.rev.sum()} 人間CR {g.cr.sum()} CR付きPR {g.pr_with_cr.sum()}"
  f" | CR/PR {g.cr.sum() / g.pr.sum():.3f} CR付きPR率 {g.pr_with_cr.sum() / g.pr.sum():.3f} CR/人間レビュー {g.cr.sum() / g.rev.sum():.3f}")
P(f" 人間レビューが1件以上ある PR に限ると: PR {rv.pr_id.nunique()} CR/PR {g.cr.sum() / rv.pr_id.nunique():.3f}")
gg = g[g.pr >= 100].cr_per_pr
P(f" repo 別 CR/PR(PR>=100 の {len(gg)} repo): 中央値 {gg.median():.3f} 最小 {gg.min():.3f} 最大 {gg.max():.3f}  CR が1件以上の repo {int((g.cr > 0).sum())}")
P(f" 上位 CR repo: " + str(g.sort_values("cr", ascending=False).head(8)[["pr", "cr"]].to_dict("index")))
P("\n== 共通 5 repo: AIDev(エージェント作者 PR) vs pilot 人間作者 PR")
for r in ["dotnet/docs", "dotnet/runtime", "getsentry/sentry", "home-assistant/core", "ydb-platform/ydb"]:
    a = g.loc[g.index.str.lower() == r].iloc[0]
    P(f"  {r}: AIDev PR {a.pr} CR {a.cr} CR/PR {a.cr_per_pr:.3f} CR付き {a.pr_with_cr_rate:.3f} | pilot human PR {h.loc[r].pr} CR {h.loc[r].cr} "
      f"CR/PR {h.loc[r].cr_per_pr:.3f} CR付き {h.loc[r].pr_with_cr_rate:.3f}")
open(f"{ROOT}/work/baseline/cr_rate.txt", "w").write("\n".join(out) + "\n"); print("\n".join(out))
