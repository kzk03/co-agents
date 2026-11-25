"""各ツール呼び出しに、その時点の Claude Code の権限モードを付ける(セッション内で直前の permission-mode 行)。

default=都度確認(許可リスト以外), acceptEdits=編集は自動承認, auto=自動判定, bypassPermissions=確認なし, plan=計画モード
記録の無いセッションは NULL(不明)。
出力: data/derived/tool_calls_mode.parquet
"""
import duckdb
con = duckdb.connect()
con.sql("""create table pm as
  select session_id, turn_number as t, json_extract_string(content, '$.permissionMode') as mode
  from 'data/swe-chat/conversations.parquet' where agent = 'Claude Code' and turn_type = 'permission_mode'""")
con.sql("""copy (
  select c.*, pm.mode as perm_mode
  from 'data/derived/tool_calls.parquet' c
  asof left join pm on c.session_id = pm.session_id and c.turn_number > pm.t
) to 'data/derived/tool_calls_mode.parquet' (format parquet)""")
print(con.sql("""select coalesce(perm_mode,'(unknown)') mode, count(*) calls, count(*) filter (where outcome<>'ok') hits,
   round(1000.0*hits/calls,2) per_mille,
   round(1000.0*count(*) filter (where outcome<>'ok' and action not in ('plan_approval','question'))
         / nullif(count(*) filter (where action not in ('plan_approval','question')),0),2) per_mille_actions_only
   from 'data/derived/tool_calls_mode.parquet' group by 1 order by calls desc""").df().to_string())
print(con.sql("""select action, count(*) calls, round(1000.0*count(*) filter (where outcome<>'ok')/count(*),2) per_mille_default
   from 'data/derived/tool_calls_mode.parquet' where perm_mode='default' and not is_entireio
   group by 1 having count(*)>=500 order by 3 desc limit 15""").df().to_string())
