"""各ツール呼び出しに、ログから機械的に取れる「条件」を付け、条件付きの行為(action_c)を作る。

条件:
  requested : 直前の人の発話(中断の行は除く)に、その行為を指す語があるか(行為ごとの語彙。英語+日本語)
  target    : git_push の宛先が main/master か(コマンドの引数、無ければセッションのブランチ)、--force の有無
  tested    : 直前の人の発話のあとに test_build を実行していたか
  depth     : 直前の人の発話からのツール呼び出し数(1-5 / 6-30 / 31+)
action_c は「重い行為」(CONSEQUENTIAL)にだけ requested を付け、git_push には target も付ける。
その他の行為は action のまま(条件で割ると疎になりすぎるため)。
出力: data/derived/tool_calls_cond.parquet(tool_calls_mode の全列 + 条件列)
"""
import re

import duckdb
import numpy as np
import pandas as pd

REQ = {
    "git_commit":   r"\bcommit|コミット",
    "git_push":     r"\bpush|プッシュ|\bship\b",
    "gh_pr_create": r"\bpr\b|pull request|プルリク|\bpr作",
    "gh_pr_merge":  r"\bmerge|マージ",
    "gh_write":     r"\bissue|\bpr\b|comment|close|イシュー|コメント",
    "deploy":       r"deploy|デプロイ|release|リリース",
    "publish":      r"publish|release|リリース|公開",
    "delete":       r"delete|remove|\brm\b|clean|prune|削除|消して|消す",
    "git_history":  r"reset|rebase|revert|checkout|switch|stash|merge|branch|worktree|ブランチ|戻",
    "git_add":      r"\badd\b|stage|commit|コミット",
    "pkg_install":  r"install|\badd\b|dependenc|依存|インストール|パッケージ",
}
CONSEQUENTIAL = set(REQ)
MAIN = re.compile(r"\b(main|master)\b")

con = duckdb.connect()
con.sql("""create table up as
  select session_id, turn_number as t, content as prompt
  from 'data/swe-chat/conversations.parquet'
  where agent = 'Claude Code' and turn_type = 'user_prompt' and content not like '[Request interrupted%'""")
con.sql("""create table c as
  select c.*, up.t as prompt_t, lower(left(up.prompt, 4000)) as prompt
  from 'data/derived/tool_calls_mode.parquet' c
  asof left join up on c.session_id = up.session_id and c.turn_number > up.t""")
# 同じ発話のあとで、何回目の呼び出しか / それまでに test_build があったか
con.sql("""create table c2 as
  select *,
    row_number() over w as depth_n,
    coalesce(bool_or(action = 'test_build') over (w rows between unbounded preceding and 1 preceding), false) as tested
  from c
  window w as (partition by session_id, prompt_t order by turn_number)""")
df = con.sql("""select c2.*, s.branch as session_branch
                from c2 left join 'data/swe-chat/sessions.parquet' s using (session_id)""").df()

pats = {a: re.compile(p) for a, p in REQ.items()}
prompt = df.prompt.fillna("")
req = np.zeros(len(df), dtype=bool)
for a, p in pats.items():
    m = (df.action == a).values
    if m.any():
        req[m] = prompt[m].str.contains(p, regex=True).values
df["requested"] = np.where(df.action.isin(CONSEQUENTIAL), req, pd.NA)

is_push = df.action == "git_push"
cmd = df.command.fillna("").str.lower()
tgt_main = cmd.str.contains(MAIN) | (~cmd.str.contains(r"push\s+\S+\s+\S+") & df.session_branch.fillna("").str.lower().isin(["main", "master"]))
df["push_main"] = np.where(is_push, tgt_main, pd.NA)
df["push_force"] = np.where(is_push, cmd.str.contains(r"--force|\s-f\b|\+\w"), pd.NA)
df["depth"] = pd.cut(df.depth_n, [0, 5, 30, np.inf], labels=["1-5", "6-30", "31+"]).astype(str)

ac = df.action.copy()
m = df.action.isin(CONSEQUENTIAL)
ac[m] = df.action[m] + np.where(df.requested[m].astype(bool), "|req", "|unreq")
ac[is_push] = ac[is_push] + np.where(df.push_main[is_push].astype(bool), "|main", "|branch")
df["action_c"] = ac

df.drop(columns=["prompt"]).to_parquet("data/derived/tool_calls_cond.parquet", index=False)

# 条件ごとの拒否率(entireio を除く)
d = df[~df.is_entireio].copy()
d["hit"] = d.outcome != "ok"
pd.set_option("display.width", 200)
def tab(by, where=None):
    x = d if where is None else d[where(d)]
    g = x.groupby(by, observed=True).agg(calls=("hit", "size"), hits=("hit", "sum"))
    g["per_mille"] = (1000 * g.hits / g.calls).round(2)
    pm = x[x.perm_mode.isin(["default", "acceptEdits"])].groupby(by, observed=True).agg(c=("hit", "size"), h=("hit", "sum"))
    g["per_mille_prompting_modes"] = (1000 * pm.h / pm.c).round(2)
    g["calls_prompting_modes"] = pm.c
    return g
print("== 重い行為 × 頼まれたか")
print(tab(["action", "requested"], lambda x: x.action.isin(CONSEQUENTIAL)).to_string(), "\n")
print("== git_push × 宛先 × force")
print(tab(["push_main", "push_force"], lambda x: x.action == "git_push").to_string(), "\n")
print("== git_commit × テスト済み")
print(tab(["tested"], lambda x: x.action == "git_commit").to_string(), "\n")
print("== 自律の深さ(全行為、計画承認・質問を除く)")
print(tab(["depth"], lambda x: ~x.action.isin(["plan_approval", "question"])).to_string())
