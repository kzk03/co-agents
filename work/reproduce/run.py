"""条件A/B のレビュー生成と LLM 判定。
uv run python work/reproduce/run.py review A|B
uv run python work/reproduce/run.py judge
"""
import concurrent.futures as cf, glob, json, os, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
W = os.path.join(ROOT, "work/reproduce")
# v1: 環境変数で標本を切り替え(既定は v0 と同じ AIDev)。ghhuman は REPRO_SET=gh
SET = os.environ.get("REPRO_SET", "aidev")
DATA = os.path.join(W, "data" if SET == "aidev" else "data_gh"); RES = os.path.join(W, "results" if SET == "aidev" else "results_gh")
CTXC = os.path.join(W, "ctxc" if SET == "aidev" else "ctxc_gh")
CWD = os.path.join(W, "_cwd"); os.makedirs(CWD, exist_ok=True); os.makedirs(RES, exist_ok=True)
DENY = "Bash,Read,Write,Edit,WebFetch,WebSearch,Agent,Glob,Grep,TodoWrite,ToolSearch,Skill,NotebookEdit"

INSTR = """You are a maintainer of this repository. Review the pull request below (it was authored by an AI coding agent).
List the issues for which you would REQUEST CHANGES before merging, most important first.
For each: target (file/location), what is wrong, how it should be fixed. Design, policy, scope and project-convention concerns are allowed.
At most 10 items. If no change is needed, answer "none". Output only the numbered list."""


ABORT = os.path.join(W, "_ABORT")  # 利用上限エラーを検知したら作成。以後の呼び出しをしない(予算の浪費防止)


def claude(prompt, model="sonnet"):
    t = time.time()
    if os.path.exists(ABORT):
        return dict(text="skipped: _ABORT present", sec=0, is_error=True, skipped=True)
    r = subprocess.run(["claude", "-p", "--model", model, "--max-turns", "1", "--disallowedTools", DENY, "--output-format", "json"],
                       input=prompt, capture_output=True, text=True, cwd=CWD, timeout=900)
    with open(os.path.join(W, "_calls.log"), "a") as lg:
        lg.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{model}\t{len(prompt)}\t{r.returncode}\n")
    try:
        j = json.loads(r.stdout)
        out = dict(text=j.get("result", ""), cost=j.get("total_cost_usd"), sec=round(time.time() - t, 1), is_error=j.get("is_error"),
                    usage=j.get("usage"))
        if out["is_error"] and "limit" in (out["text"] or ""):
            open(ABORT, "w").write(out["text"])
        return out
    except Exception:
        return dict(text=r.stdout, err=r.stderr[-500:], sec=round(time.time() - t, 1), is_error=True)


def review_prompt(rec, cond):
    if cond == "Cr":  # v1 追加: PR 本文をレビュー時点の本文に差し替えた条件C
        rec = dict(rec, pr_body=open(os.path.join(W, "data_at_review_body", f"{rec['sid']}.txt")).read())
        cond = "C"
    p = [INSTR, f"\n# Repository: {rec['repo']}\n# PR title: {rec['title']}\n# PR description:\n{rec['pr_body'] or '(empty)'}\n"]
    if cond in ("B", "C"):
        p.append("# Repository context (files at the reviewed commit / base)\n")
        for k, v in rec["context"].items():
            p.append(f"## {k}\n```\n{v}\n```\n")
    if cond == "C":  # v1: 上流の情報(リンク Issue 本文 + 対象レビューより前の PR 上の会話)
        c = json.load(open(os.path.join(CTXC, f"{rec['sid']}.json")))
        p.append("# Linked issue (the request the PR addresses)\n" + (c.get("issue_text") or "(no linked issue found)") + "\n")
        p.append("# PR conversation so far (before your review; oldest first)\n" + (c.get("discussion") or "(no prior conversation)") + "\n")
    p.append(f"# Diff ({rec['n_files']} files{', TRUNCATED' if rec['truncated'] else ''})\n{rec['diff']}")
    return "\n".join(p)


def review(cond, only=None):
    recs = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(DATA, "[GH][0-9]*.json")))]
    if only:
        recs = [r for r in recs if r["sid"] in only]
    def one(rec):
        out = os.path.join(RES, f"{rec['sid']}_{cond}.json")
        if os.path.exists(out) and not json.load(open(out)).get("is_error"):
            return
        r = claude(review_prompt(rec, cond)); r["sid"] = rec["sid"]; r["cond"] = cond
        json.dump(r, open(out, "w"), ensure_ascii=False, indent=1); print(rec["sid"], cond, r["sec"], r.get("cost"), flush=True)
    with cf.ThreadPoolExecutor(4) as ex:
        list(ex.map(one, recs))


JUDGE = """You judge whether an LLM reviewer reproduced a human reviewer's objection on a pull request.
Step 1: identify the human's MAIN objection = the reason that most directly caused the change request (one sentence).
Step 2: for each LLM review (A and B), decide whether it contains substantially the same objection:
- yes: same problem with the same direction of fix (wording/granularity may differ; a different line is fine if it is the same problem)
- partial: touches the same location/concern area but the direction or substance falls short, OR only a secondary (non-main) human point is reproduced
- no: nothing corresponding to the main objection
If the human relies only on CI logs/run results, it is still "yes" if the LLM points to the same defect.
Output ONLY one JSON object, no code fences:
{"main":"<one sentence>","A":"yes|partial|no","A_match":"<LLM item number or quote, or empty>","B":"yes|partial|no","B_match":"..."}
"""


def human_text(sid):
    smp = {r["sid"]: r for r in json.load(open(os.path.join(ROOT, "outputs/aidev/sample100.json")))}[sid]
    b = smp["body"] if isinstance(smp["body"], str) else "(none)"
    return f"BODY: {b}\n" + "\n".join(f"[inline {i['path']}] {i['body']}" for i in smp["inline"])


def judge():
    v0 = {x["sid"] for x in json.load(open(os.path.join(DATA, "_fetch_log.json"))) if x["status"] == "OK"}  # v0 の 18件のみ
    recs = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(DATA, "G*.json"))) if os.path.basename(f)[:-5] in v0]
    def one(rec):
        sid = rec["sid"]; out = os.path.join(RES, f"{sid}_judge.json")
        if os.path.exists(out) and not json.load(open(out)).get("is_error"):
            return
        a = json.load(open(os.path.join(RES, f"{sid}_A.json")))["text"]; b = json.load(open(os.path.join(RES, f"{sid}_B.json")))["text"]
        p = f"{JUDGE}\n# PR: {rec['repo']} — {rec['title']}\n\n# HUMAN REVIEW (CHANGES_REQUESTED)\n{human_text(sid)}\n\n# LLM REVIEW A\n{a}\n\n# LLM REVIEW B\n{b}\n"
        r = claude(p); r["sid"] = sid
        json.dump(r, open(out, "w"), ensure_ascii=False, indent=1); print(sid, "judge", r["sec"], r.get("cost"))
    with cf.ThreadPoolExecutor(4) as ex:
        list(ex.map(one, recs))


JUDGE_V1 = """You judge whether LLM reviewers reproduced a human reviewer's objection on a pull request.
Step 1: identify the human's MAIN objection = the reason that most directly caused the change request (one sentence).
Step 2: for each LLM review (R1, R2, R3), decide whether it contains substantially the same objection:
- yes: same problem with the same direction of fix (wording/granularity may differ; a different line is fine if it is the same problem)
- partial: touches the same location/concern area but the direction or substance falls short, OR only a secondary (non-main) human point is reproduced
- no: nothing corresponding to the main objection
If the human relies only on CI logs/run results, it is still "yes" if the LLM points to the same defect.
For each review also give the item NUMBER (1-based, in that review's numbered list) of the best matching item, or 0 if none.
Output ONLY one JSON object, no code fences:
{"main":"<one sentence>","R1":"yes|partial|no","R1_item":0,"R2":"yes|partial|no","R2_item":0,"R3":"yes|partial|no","R3_item":0}
"""


def human_text_any(sid):
    if sid.startswith("G"):
        return human_text(sid)
    smp = {r["sid"]: r for r in json.load(open(os.path.join(ROOT, "outputs/ghhuman/sample100.json")))}[sid]
    import ast
    b = smp["body"] if isinstance(smp["body"], str) and smp["body"] not in ("", "nan") else "(none)"
    try:
        cm = ast.literal_eval(smp["comments"]) if isinstance(smp["comments"], str) else smp["comments"]
    except Exception:
        cm = []
    return f"BODY: {b}\n" + "\n".join(f"[inline {i.get('path')}] {i.get('body')}" for i in cm)


def perm(sid, conds):
    import random
    o = list(conds); random.Random(20261021 + int(sid[1:])).shuffle(o); return o


def judge_v1(conds=("A", "B", "C")):
    """盲検判定: 群ラベル・条件名を伏せ、R1..Rk を PR ごとに並べ替える。"""
    recs = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(DATA, "[GH][0-9]*.json")))]
    def one(rec):
        sid = rec["sid"]; out = os.path.join(RES, f"{sid}_judge_v1.json")
        if os.path.exists(out) and not json.load(open(out)).get("is_error"):
            return
        avail = [c for c in conds if os.path.exists(os.path.join(RES, f"{sid}_{c}.json"))]
        order = perm(sid, avail)
        p = JUDGE_V1.replace("R1, R2, R3", ", ".join(f"R{i+1}" for i in range(len(order))))
        if len(order) != 3:
            p = p.replace('"R1":"yes|partial|no","R1_item":0,"R2":"yes|partial|no","R2_item":0,"R3":"yes|partial|no","R3_item":0',
                          ",".join(f'"R{i+1}":"yes|partial|no","R{i+1}_item":0' for i in range(len(order))))
        p += f"\n# PR: {rec['repo']} — {rec['title']}\n\n# HUMAN REVIEW (CHANGES_REQUESTED)\n{human_text_any(sid)}\n"
        for i, c in enumerate(order):
            p += f"\n# LLM REVIEW R{i+1}\n{json.load(open(os.path.join(RES, f'{sid}_{c}.json')))['text']}\n"
        r = claude(p); r["sid"] = sid; r["order"] = order
        json.dump(r, open(out, "w"), ensure_ascii=False, indent=1); print(sid, "judge_v1", r["sec"], r.get("cost"), flush=True)
    with cf.ThreadPoolExecutor(4) as ex:
        list(ex.map(one, recs))


if __name__ == "__main__":
    {"review": lambda: review(sys.argv[2], sys.argv[3].split(",") if len(sys.argv) > 3 else None), "judge": judge,
     "judge_v1": lambda: judge_v1(tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else ("A", "B", "C"))}[sys.argv[1]]()
