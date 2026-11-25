"""Claude Code の全ツール呼び出しを行為の種類に分類し、人の拒否・中断を機械的に紐づける。

判定はログの構造的な印だけで行う(自由文の解釈はしない)。
  rejected    : tool_result が "The user doesn't want to proceed with this tool use"
                ("the user said:" 以降があれば feedback として保存)
                ※ 直後の "[Request interrupted by user for tool use]" は拒否に付随する行なので別に数えない
  interrupted : tool_result に "Request interrupted by user"(実行中の中断)
行為の分類: Bash は scripts/actions.py、それ以外はツール名で決める。
出力: data/derived/tool_calls.parquet   1 行 = 1 ツール呼び出し
"""
import sys

import duckdb
import pandas as pd

sys.path.insert(0, "scripts")
from actions import classify_command  # noqa: E402

C = "'data/swe-chat/conversations.parquet'"
con = duckdb.connect()

con.sql(f"""
create table calls as
select session_id, user_id, repo_id, turn_number, timestamp, tool_name, tool_call_id, command, file_path
from {C}
where agent = 'Claude Code' and turn_type = 'tool_use' and tool_call_id is not null""")

cmds = con.sql("select distinct command from calls where tool_name = 'Bash'").df()
cmds["bash_action"] = cmds.command.map(classify_command)
con.register("cmd_map", cmds)

con.sql(f"""
create table results as
select tool_call_id,
       any_value(case
         when content like 'The user doesn''t want to proceed with this tool use%' then 'rejected'
         when content like '%Request interrupted by user%' then 'interrupted' end) as outcome,
       any_value(case when content like '%the user said:%'
         then trim(regexp_replace(substr(content, strpos(content, 'the user said:') + 14),
                                  '\\s*Note: The user''s next message may contain.*$', '', 's')) end) as feedback
from {C}
where agent = 'Claude Code' and turn_type = 'tool_result'
  and (content like 'The user doesn''t want to proceed%' or content like '%Request interrupted by user%')
group by 1""")

# user_id は会話・セッション表とも約 1/3 が空。次の順で補う(user_inferred で区別):
#   1) セッションの user_id  2) リポジトリの既知ユーザーが 1 人ならその人  3) 'repo:' || repo_id
con.sql("""
create table user_map as
with known as (
  select repo_id, count(distinct user_id) n, any_value(user_id) u
  from 'data/swe-chat/sessions.parquet' where user_id is not null group by 1)
select s.session_id,
       coalesce(s.user_id, case when k.n = 1 then k.u end, 'repo:' || s.repo_id) as user_key,
       s.user_id is null as user_inferred
from 'data/swe-chat/sessions.parquet' s left join known k using (repo_id)""")

con.sql("""
copy (
  select c.* replace (m.user_key as user_id), m.user_inferred,
         case
           when c.tool_name = 'Bash' then coalesce(m.bash_action, 'bash_other')
           when c.tool_name in ('Edit','Write','MultiEdit','NotebookEdit') then 'file_edit'
           when c.tool_name = 'ExitPlanMode' then 'plan_approval'
           when c.tool_name = 'AskUserQuestion' then 'question'
           when c.tool_name in ('Agent','Task') then 'subagent'
           when c.tool_name in ('Read','Glob','Grep','LS') then 'read'
           when c.tool_name in ('WebFetch','WebSearch') then 'web'
           when c.tool_name like 'mcp__%' then 'mcp'
           else 'tool:' || c.tool_name end as action,
         coalesce(r.outcome, 'ok') as outcome,
         r.feedback,
         rp.url like '%/entireio/cli' as is_entireio
  from calls c
  left join cmd_map m on c.tool_name = 'Bash' and m.command is not distinct from c.command
  left join results r using (tool_call_id)
  left join user_map m using (session_id)
  left join 'data/swe-chat/repositories.parquet' rp on rp.repo_id = c.repo_id
) to 'data/derived/tool_calls.parquet' (format parquet)""")

print(con.sql("""select outcome, count(*) n from 'data/derived/tool_calls.parquet'
                 group by 1 order by 2 desc""").df().to_string())
