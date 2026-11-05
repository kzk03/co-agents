"""AIDev: エージェント PR の diff から「人間が決めるべき決定」を検出できるか(実現可能性の確認)。

実行(このディレクトリで):
  uv run scripts/aidev_diff_decisions.py sample   # A: merged 60件(エージェントごと10件、1 repo 1件、seed=42)+ B: 既存 CR サンプルの H 系
  uv run scripts/aidev_diff_decisions.py fetch    # gh api で PR の diff を取得
  uv run scripts/aidev_diff_decisions.py heur     # 正規表現による簡易検出
  uv run scripts/aidev_diff_decisions.py llm      # claude -p で決定を抽出(diff の行を原文で引用させる)
  uv run scripts/aidev_diff_decisions.py stats
出力: outputs/aidev_diff/
"""
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
D = os.path.join(ROOT, "data", "aidev")
OUT = os.path.join(ROOT, "outputs", "aidev_diff")
DIFFS = os.path.join(OUT, "diffs")
LLM = os.path.join(OUT, "llm")
BOT = re.compile(r"(?:\[bot\]|bot$|-bot\b|copilot|coderabbit|sourcery|gemini-code-assist|codex|devin|cursor|claude|jules)", re.I)
DENY = "Bash,Read,Write,Edit,WebFetch,WebSearch,Agent,Glob,Grep,TodoWrite,ToolSearch,Skill,NotebookEdit"
MAX_DIFF = 60000


def repo_of(url):
    return url.split("github.com/")[1].split("/pull/")[0]


def sample():
    pr = pd.read_parquet(f"{D}/pull_request.parquet")
    m = pr[pr["merged_at"].notna()].sample(frac=1, random_state=42)
    pick, used = [], set()
    for agent in sorted(m["agent"].unique()):
        n = 0
        for _, r in m[m["agent"] == agent].iterrows():
            if n >= 10 or r["repo_id"] in used:
                continue
            pick.append(dict(sid=f"A{len(pick) + 1:03d}", set="A", pr_id=int(r["id"]), agent=agent, outcome="merged",
                             repo=repo_of(r["html_url"]), number=int(r["number"]), html_url=r["html_url"], title=r["title"]))
            used.add(r["repo_id"]); n += 1
    irr = pd.read_csv(os.path.join(ROOT, "outputs/aidev/irr/irr_merged.csv"))
    hs = set(irr[irr["majority"].str.startswith("H")]["sid"])
    for s in json.load(open(os.path.join(ROOT, "outputs/aidev/sample100.json"))):
        if s["sid"] not in hs:
            continue
        concern = [s.get("body") or ""] + [c["body"] for c in s.get("inline", [])]
        pick.append(dict(sid="B" + s["sid"][1:], set="B", pr_id=int(s["pr_id"]), agent=s["agent"], outcome=s["outcome"],
                         repo=s["repo"], number=int(s["html_url"].rsplit("/", 1)[1]), html_url=s["html_url"], title=s["title"],
                         src_sid=s["sid"], reviewer_concern="\n---\n".join(c for c in concern if isinstance(c, str) and c.strip())))
    os.makedirs(OUT, exist_ok=True)
    json.dump(pick, open(f"{OUT}/sample.json", "w"), ensure_ascii=False, indent=1)
    print("A", sum(p["set"] == "A" for p in pick), "B", sum(p["set"] == "B" for p in pick))


def fetch():
    os.makedirs(DIFFS, exist_ok=True)
    s = json.load(open(f"{OUT}/sample.json"))

    def one(p):
        f = f"{DIFFS}/{p['sid']}.diff"
        if os.path.exists(f):
            return p["sid"], "cached"
        r = subprocess.run(["gh", "api", f"repos/{p['repo']}/pulls/{p['number']}", "-H", "Accept: application/vnd.github.v3.diff"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return p["sid"], "error: " + r.stderr.strip()[:200]
        open(f, "w").write(r.stdout)
        return p["sid"], "ok"
    with ThreadPoolExecutor(8) as ex:
        res = dict(ex.map(one, s))
    json.dump(res, open(f"{OUT}/fetch_log.json", "w"), indent=1)
    print(pd.Series([v.split(":")[0] for v in res.values()]).value_counts().to_dict())


# 簡易検出: ファイルパスと追加・削除行のパターン
PATH_RULES = {
    "dependency": r"(^|/)(package\.json|requirements[^/]*\.txt|pyproject\.toml|setup\.py|go\.mod|Cargo\.toml|pom\.xml|build\.gradle(\.kts)?|Gemfile|composer\.json|[^/]*\.csproj)$",
    "schema_migration": r"(migrations?/|\.sql$|schema\.(prisma|graphql|json|ya?ml)$|\.proto$)",
    "ci_workflow": r"(^\.github/workflows/|\.gitlab-ci\.yml$|Jenkinsfile$|azure-pipelines)",
    "config": r"(\.(ya?ml|toml|ini|cfg|conf|env)$|(^|/)config[^/]*\.(json|js|ts|py)$|Dockerfile$)",
}
REMOVED_GUARD = re.compile(r"^-\s*.*\b(raise|throw|assert|panic|permission|authori[sz]|authenticat|validate|sanitize|csrf|cors)\b", re.I)
SECURITY_ADD = re.compile(r"^\+.*\b(password|secret|token|api[_-]?key|chmod|sudo|eval\(|exec\(|verify\s*=\s*False|allow_origins|disable)\b", re.I)
SIG = re.compile(r"^([-+])\s*(export\s+|public\s+|pub\s+(fn|struct)|def\s+[A-Za-z]|func\s+[A-Z]|function\s+\w+|class\s+\w+)")


def parse(diff):
    files, cur = {}, None
    for line in diff.splitlines():
        if line.startswith("diff --git"):
            cur = line.split(" b/", 1)[1] if " b/" in line else line
            files[cur] = []
        elif cur and not line.startswith(("+++", "---")):
            files[cur].append(line)
    return files


def is_test(path):
    return bool(re.search(r"(^|/)(tests?|__tests__|spec)(/|$)|(_test|\.test|\.spec|test_)[^/]*$", path, re.I))


def heur():
    s = json.load(open(f"{OUT}/sample.json"))
    rows = []
    for p in s:
        f = f"{DIFFS}/{p['sid']}.diff"
        if not os.path.exists(f):
            continue
        files = parse(open(f).read())
        r = dict(sid=p["sid"], n_files=len(files), n_lines=sum(len(v) for v in files.values()))
        for k, rx in PATH_RULES.items():
            r[k] = sum(bool(re.search(rx, path)) and not is_test(path) for path in files)
        src = {k: v for k, v in files.items() if not is_test(k)}
        r["guard_removed"] = sum(bool(REMOVED_GUARD.match(l)) for v in src.values() for l in v)
        r["security_added"] = sum(bool(SECURITY_ADD.match(l)) for v in src.values() for l in v)
        r["signature_removed"] = sum(1 for v in src.values() for l in v if (m := SIG.match(l)) and m.group(1) == "-")
        r["test_removed"] = sum(1 for k, v in files.items() if is_test(k) for l in v if re.match(r"^-\s*(def test|it\(|test\(|@Test)", l))
        rows.append(r)
    d = pd.DataFrame(rows)
    d.to_csv(f"{OUT}/heur.csv", index=False)
    print(d.describe().T[["mean", "max"]].to_string())


PROMPT = """あなたはソフトウェア工学の研究のコーダーです。AI エージェントが作った GitHub PR の diff を読み、
**diff の中で下されている「人間が下すべき決定」** をすべて抜き出してください。

## 人間が下すべき決定とは
複数の妥当な選択肢があり、その選択がコード変更の外(利用者、他のシステム、運用、法務、セキュリティ、プロジェクトの方針)に影響し、
メンテナによって答えが分かれうるもの。タスクの依頼文やコードの文脈から一意に決まるものは含めない。

含める例:
- api_contract: 公開 API・CLI・設定項目のシグネチャや意味・デフォルトの変更、後方互換性を壊す変更、非推奨化
- dependency: 新しい依存の追加、メジャー更新、依存の削除・置き換え
- data_schema: データ形式・DB スキーマ・保存形式・マイグレーション
- security_policy: 認証・認可・検証・サニタイズ・秘密情報の扱いの変更、ガード節や安全チェックの削除・緩和
- error_policy: 失敗時の振る舞い(例外を握りつぶす、リトライ、フォールバック、タイムアウト値)の選択
- scope: 依頼にない機能の追加、既存機能の削除・挙動変更
- user_facing: 利用者に見える文言・UI・ログ・ドキュメント上の約束の変更
- architecture: 新しいモジュール構成・パターン・技術の導入
- test_policy: テストの削除・スキップ・期待値の書き換え・閾値の緩和
- other

含めない: 命名・整形・局所的なリファクタリング・依頼から一意に決まる実装・テストの追加。

## 人間の跡
下の「人間が書いたテキスト」(Issue、依頼、レビュー、コメント)と「PR 本文」を見て、各決定について:
- human_trace: "requested"(人間の依頼・Issue にその選択が明示されている) / "discussed"(人間のレビュー・コメントで言及または承認されている) / "agent_only"(エージェントの PR 本文にだけ書かれている) / "none"(どこにも言及がない)
- PR 本文は通常エージェントが書いている。ただし人間の依頼が引用されている場合がある(その部分は requested とみなす)

## 出力
JSON だけを出力する(前後に文章を書かない):
{"decisions": [{"kind": "...", "what": "何をどう決めたか(日本語1文)", "alternatives": "他にありえた選択(日本語、短く)",
  "evidence": "diff の該当行を1行、+ または - を含めて原文どおりにコピー", "file": "パス",
  "stage": 2 か 3(2=証拠の解釈・評価、3=方針・設計の選択), "confidence": "high" | "medium" | "low",
  "human_trace": "...", "trace_quote": "根拠となる人間テキストの原文(なければ空)"}],
 "note": "全体についての短い注記(任意)"}
決定が一つもなければ {"decisions": [], "note": "..."}。
"""


def human_text(p, pr, cm, rv, rc):
    out = []
    pu = pr.loc[pr["id"] == p["pr_id"], "user"]
    pu = pu.iloc[0] if len(pu) else None

    def human(df):
        return df[(df["user_type"] == "User") & ~df["user"].fillna("").str.contains(BOT.pattern, regex=True) & (df["user"] != pu)]
    for _, r in human(cm[cm["pr_id"] == p["pr_id"]]).iterrows():
        out.append(f"[comment by {r['user']}] {r['body']}")
    for _, r in human(rv[rv["pr_id"] == p["pr_id"]]).iterrows():
        if isinstance(r["body"], str) and r["body"].strip():
            out.append(f"[review {r['state']} by {r['user']}] {r['body']}")
        for _, c in rc[rc["pull_request_review_id"] == r["id"]].iterrows():
            out.append(f"[inline on {c['path']} by {c['user']}] {c['body']}")
    return out


def llm(model="sonnet"):
    os.makedirs(LLM, exist_ok=True)
    s = json.load(open(f"{OUT}/sample.json"))
    pr = pd.read_parquet(f"{D}/pull_request.parquet", columns=["id", "user", "body"])
    cm = pd.read_parquet(f"{D}/pr_comments.parquet")
    rv = pd.read_parquet(f"{D}/pr_reviews.parquet")
    rc = pd.read_parquet(f"{D}/pr_review_comments.parquet")

    def one(p):
        f = f"{DIFFS}/{p['sid']}.diff"
        o = f"{LLM}/{model}_{p['sid']}.json"
        if not os.path.exists(f) or os.path.exists(o):
            return
        diff = open(f).read()
        body = pr.loc[pr["id"] == p["pr_id"], "body"]
        body = body.iloc[0] if len(body) and isinstance(body.iloc[0], str) else ""
        ht = human_text(p, pr, cm, rv, rc)
        msg = (PROMPT + f"\n\n## PR\nrepo: {p['repo']}\ntitle: {p['title']}\nagent: {p['agent']}\n\n## PR 本文\n{body[:8000]}\n\n"
               + "## 人間が書いたテキスト\n" + ("\n".join(ht)[:12000] or "(なし)")
               + f"\n\n## diff{'(長いので途中で打ち切り)' if len(diff) > MAX_DIFF else ''}\n{diff[:MAX_DIFF]}")
        r = subprocess.run(["claude", "-p", "--model", model, "--max-turns", "1", "--disallowedTools", DENY],
                           input=msg, capture_output=True, text=True, cwd=OUT)
        txt = r.stdout.strip()
        m = re.search(r"\{.*\}", txt, re.S)
        try:
            j = json.loads(m.group(0))
        except (AttributeError, json.JSONDecodeError):
            j = {"error": txt[:500] or r.stderr[:500]}
        j.update(sid=p["sid"], truncated=len(diff) > MAX_DIFF, n_human_text=len(ht))
        json.dump(j, open(o, "w"), ensure_ascii=False, indent=1)
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(one, s))


def norm(x):
    return re.sub(r"\s+", "", x or "")


def stats(model="sonnet"):
    s = {p["sid"]: p for p in json.load(open(f"{OUT}/sample.json"))}
    h = pd.read_csv(f"{OUT}/heur.csv").set_index("sid")
    rows, prs = [], []
    for sid, p in s.items():
        o = f"{LLM}/{model}_{sid}.json"
        if not os.path.exists(o):
            continue
        j = json.load(open(o))
        if "error" in j:
            prs.append(dict(sid=sid, set=p["set"], error=True)); continue
        diff = norm(open(f"{DIFFS}/{sid}.diff").read())
        for d in j["decisions"]:
            rows.append(dict(sid=sid, set=p["set"], agent=p["agent"], **{k: d.get(k) for k in
                             ["kind", "stage", "confidence", "human_trace", "what", "evidence", "file"]},
                             grounded=bool(norm(d.get("evidence"))) and norm(d.get("evidence")) in diff))
        prs.append(dict(sid=sid, set=p["set"], agent=p["agent"], error=False, truncated=j["truncated"],
                        n_human_text=j["n_human_text"], n_dec=len(j["decisions"])))
    d, P = pd.DataFrame(rows), pd.DataFrame(prs)
    d.to_csv(f"{OUT}/decisions_{model}.csv", index=False)
    lines = []

    def say(*a):
        x = " ".join(str(v) for v in a); print(x); lines.append(x)
    say("== PR", P.groupby("set").agg(n=("sid", "size"), errors=("error", "sum")).to_dict())
    P = P[~P["error"]]
    for st in ["A", "B"]:
        pp, dd = P[P["set"] == st], d[d["set"] == st]
        say(f"\n== set {st}: PR {len(pp)}、打ち切り {int(pp['truncated'].sum())}、人間テキストのある PR {int((pp['n_human_text'] > 0).sum())}")
        say("決定を1つ以上含む PR", int((pp["n_dec"] > 0).sum()), f"({(pp['n_dec'] > 0).mean():.0%})", "決定の総数", len(dd))
        if len(dd):
            say("引用が diff に実在", f"{dd['grounded'].mean():.0%}")
            say("kind", dd["kind"].value_counts().to_dict())
            say("confidence", dd["confidence"].value_counts().to_dict())
            say("human_trace", dd["human_trace"].value_counts().to_dict())
            hi = dd[(dd["confidence"] != "low") & dd["grounded"]]
            n_none = hi[hi["human_trace"].isin(["none", "agent_only"])]["sid"].nunique()
            say("confidence≠low かつ引用実在の決定", len(hi), "/ 人間の跡なしの決定を含む PR", n_none, f"({n_none / len(pp):.0%})")
    # 簡易検出との対応(PR 単位)
    flag = h[[c for c in h.columns if c not in ("n_files", "n_lines")]].gt(0).any(axis=1)
    P["heur_any"] = P["sid"].map(flag)
    P["llm_any"] = P["n_dec"] > 0
    say("\n== 簡易検出 × LLM(PR 単位、set A)")
    say(pd.crosstab(P[P["set"] == "A"]["heur_any"], P[P["set"] == "A"]["llm_any"]).to_string())
    open(f"{OUT}/stats_{model}.txt", "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    {"sample": sample, "fetch": fetch, "heur": heur, "llm": llm, "stats": stats}[sys.argv[1]](*sys.argv[2:])
