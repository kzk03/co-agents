"""「頼まれていない重い行為への拒否」(留保に近い信号)と「頼まれた重い行為への拒否」(やり方の修正に近い)で、
個人の持続性を比べる。

09 と同じ分割(ユーザーごとに前半/後半、4 セッション以上)。重い行為 a ごとに、
train で (a, 条件 r) を拒否したユーザーについて、test での (a, r) の拒否数 O と、
他ユーザーの (a, r) の拒否率から予想される E を比べ、行為をまたいでプールする。
  r = unreq / req。比較として「train で拒否なし」の組も出す。
ブートストラップはユーザー単位 1000 回。出力: data/derived/persistence_requested.csv
"""
import os

import duckdb
import numpy as np
import pandas as pd

RNG = np.random.default_rng(20261121)
MIN_SESSIONS = 4
MODE = os.environ.get("PERM_MODES")
MODE_SQL = (" and perm_mode in (" + ",".join(repr(m) for m in MODE.split(",")) + ")") if MODE else ""

df = duckdb.sql(f"""
  select user_id, session_id, action, requested, outcome <> 'ok' as hit, timestamp
  from 'data/derived/tool_calls_cond.parquet'
  where requested is not null and not is_entireio{MODE_SQL}""").df()
df["key"] = df.action + "|" + np.where(df.requested.astype(bool), "req", "unreq")
df["cond"] = np.where(df.requested.astype(bool), "req", "unreq")

# 分割は全呼び出しのセッションで決める(重い行為が無いセッションも数に入れる)
ses = duckdb.sql("""select user_id, session_id, min(timestamp) s from 'data/derived/tool_calls.parquet'
                    where not is_entireio group by all""").df()
ses["n"] = ses.groupby("user_id").session_id.transform("size")
ses = ses[ses.n >= MIN_SESSIONS].copy()
ses["rank"] = ses.groupby("user_id").s.rank(method="first")
ses["split"] = np.where(ses["rank"] <= ses.n / 2, "train", "test")
df = df.merge(ses[["session_id", "split"]], on="session_id")

tot = df.groupby("key").agg(c=("hit", "size"), h=("hit", "sum"))
ua = df.groupby(["user_id", "key"]).agg(cu=("hit", "size"), hu=("hit", "sum"))
tr = df[df.split == "train"].groupby(["user_id", "key"]).agg(ht=("hit", "sum"))
te = df[df.split == "test"].groupby(["user_id", "key", "cond"]).agg(n=("hit", "size"), o=("hit", "sum")).reset_index()
te = te.join(tot, on="key").join(ua, on=["user_id", "key"]).join(tr, on=["user_id", "key"]).fillna({"ht": 0})
te["g"] = ((te.h - te.hu) / (te.c - te.cu).replace(0, np.nan)).fillna(0)
te["e"] = te.n * te.g
te["train_hit"] = np.where(te.ht > 0, "yes", "no")


def summarize(t):
    return t.groupby(["cond", "train_hit"]).agg(n=("n", "sum"), O=("o", "sum"), E=("e", "sum"),
                                                 users=("user_id", "nunique"))


point = summarize(te)
groups = {u: g for u, g in te.groupby("user_id")}
users = list(groups)
boots = []
for _ in range(1000):
    s = pd.concat([groups[u] for u in RNG.choice(users, len(users), replace=True)])
    b = summarize(s)
    boots.append((b.O / b.E.replace(0, np.nan)))
B = pd.concat(boots, axis=1)
point["O_over_E"] = point.O / point.E
point["lo"] = B.quantile(0.025, axis=1)
point["hi"] = B.quantile(0.975, axis=1)
point = point.round(3)
point.to_csv(f"data/derived/persistence_requested{'_' + MODE.replace(',', '_') if MODE else ''}.csv")
print(point.to_string())
