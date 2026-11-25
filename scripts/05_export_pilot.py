"""パイロット 30 セッションを、人が読んで注釈できる Markdown に書き出す。

出力(docs/ は git 管理外):
  docs/pilot/sessions/NN_owner__repo.md   時系列の会話(メタデータ行は省く)
  docs/pilot/defs/NN_owner__repo.md       セッション当時の定義ファイルの中身
  docs/pilot/annotations.csv              注釈用の空の表(1 行 = 1 つの判断)
  data/derived/pilot_conversations.parquet  元の行(分析用)

注釈者の先入観を避けるため、データセットの prompt_pushback ラベルは表示しない。
"""
import json, os, subprocess
import duckdb, pandas as pd

OUT = "docs/pilot"
TOOL_RESULT_MAX = 300
REJECT_MARKS = ("doesn't want to proceed", "user rejected", "Request interrupted",
                "tool use was rejected", "The user denied")

pilot = pd.read_csv("data/derived/pilot_sessions.csv")
status = pd.read_csv("data/repos/_status.csv").set_index("repo_id").path.to_dict()
defs = duckdb.sql("select session_id, commit from 'data/derived/session_defs.parquet'").df() \
    .set_index("session_id").commit.to_dict()

con = duckdb.connect()
con.sql("""create table p as select * from 'data/swe-chat/conversations.parquet'
           where session_id in (select session_id from read_csv('data/derived/pilot_sessions.csv'))""")
con.sql("copy p to 'data/derived/pilot_conversations.parquet'")

def short_tool_input(tool, raw):
    try:
        d = json.loads(raw or "{}")
    except Exception:
        return (raw or "")[:200]
    for k in ("command", "file_path", "pattern", "url", "description", "prompt", "query"):
        if d.get(k):
            v = str(d[k]).replace("\n", " ")
            return f"{k}={v[:200]}"
    return json.dumps(d, ensure_ascii=False)[:200]

def block(text):
    return "\n".join("> " + l for l in (text or "").strip().splitlines()) or "> (空)"

os.makedirs(f"{OUT}/sessions", exist_ok=True)
os.makedirs(f"{OUT}/defs", exist_ok=True)
ann_rows = []
for i, s in enumerate(pilot.itertuples(), 1):
    slug = f"{i:02d}_" + s.url.removeprefix("https://github.com/").replace("/", "__")
    rows = con.sql(f"""select * from p where session_id = '{s.session_id}'
                       order by turn_number, content_block_index""").df()
    lines = [f"# {i:02d} {s.url}", "",
             f"- session_id: `{s.session_id}`",
             f"- 開始: {s.t} / プロンプト数: {s.prompt_count}",
             f"- 定義ファイル: {s.def_files.replace('|', ', ')}(中身は ../defs/{slug}.md)",
             f"- viewer: {s.viewer_url_hf}", "",
             "各見出しの `[t=番号]` は turn_number。注釈では この番号で場所を指す。", ""]
    for r in rows.itertuples():
        t, kind, content = r.turn_number, r.turn_type, r.content or ""
        if kind == "user_prompt":
            lines += [f"### [t={t}] 👤 USER", block(content), ""]
        elif kind == "system_injected":
            lines += [f"#### [t={t}] ⚙ system_injected", block(content[:500]), ""]
        elif kind == "assistant_response":
            lines += [f"### [t={t}] 🤖 ASSISTANT", block(content), ""]
        elif kind == "tool_use":
            lines += [f"- [t={t}] 🔧 `{r.tool_name}` {short_tool_input(r.tool_name, r.tool_input_json or content)}"]
        elif kind == "tool_result":
            rejected = any(m.lower() in content.lower() for m in REJECT_MARKS)
            if rejected:
                lines += ["", f"#### [t={t}] ⛔ tool_result(拒否・中断)", block(content), ""]
            else:
                c = content.replace("\n", " ")
                lines += [f"  - [t={t}] ↳ {c[:TOOL_RESULT_MAX]}{'…' if len(c) > TOOL_RESULT_MAX else ''}"]
        elif kind == "queue_operation" and r.queue_op_subtype and r.queue_op_subtype.startswith("user_prompt"):
            lines += [f"- [t={t}] 📨 queue: {r.queue_op_subtype} {content[:300].replace(chr(10), ' ')}"]
        elif kind in ("permission_mode", "mode"):
            lines += [f"- [t={t}] 🔐 {kind}: {content[:150].replace(chr(10), ' ')}"]
    open(f"{OUT}/sessions/{slug}.md", "w").write("\n".join(lines) + "\n")

    # 定義ファイル(当時の版)。blobless clone なので git show で本体を取りに行く。
    commit, path = defs.get(s.session_id), status.get(s.repo_id)
    d = [f"# {i:02d} {s.url} の定義ファイル(commit {commit})", ""]
    for f in s.def_files.split("|"):
        r = subprocess.run(["git", "-C", path, "show", f"{commit}:{f}"],
                           capture_output=True, text=True, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        d += [f"## {f}", "", "````markdown", r.stdout if r.returncode == 0 else f"(取得失敗: {r.stderr.strip()})", "````", ""]
    open(f"{OUT}/defs/{slug}.md", "w").write("\n".join(d))
    ann_rows.append(dict(no=f"{i:02d}", session_id=s.session_id, url=s.url))
    print("ok", slug, len(rows), flush=True)

cols = ["no", "session_id", "url", "turn", "発話の引用", "判断の種類(却下/中断/押し返し/書かせた/その他)",
        "Human.mdに書くべきか(yes/no/迷う)", "留保か委任か", "何について", "何を", "どんなときに",
        "誰が決めるか", "どう確認するか", "定義ファイルに対応規則があるか", "メモ"]
pd.DataFrame(ann_rows).reindex(columns=cols).to_csv(f"{OUT}/annotations.csv", index=False, encoding="utf-8-sig")
print("done")
