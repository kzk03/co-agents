"""Write upstream_me.csv from my_labels.py + material (written before reading sonnet outputs)."""
import json, os, re
import pandas as pd
from my_labels import AGENT, HUMAN
BASE = os.path.dirname(os.path.abspath(__file__))
rows = []
for side, lab in [("agent", AGENT), ("human", HUMAN)]:
    for l in open(os.path.join(BASE, f"material_{side}.jsonl")):
        r = json.loads(l)
        if side == "human" and r["req_src"] != "issue":
            m = dict(me="U4", me_dec="NA", me_conf="H", me_note="リンクIssueなし(依頼文なし)", me_req_quote="")
        else:
            m = lab[r["sid"]]
        rev = re.sub(r"\s+", " ", r["review"].replace("BODY: (empty)", "").replace("BODY: nan", "").replace("BODY: ", ""))[:200].strip()
        rows.append(dict(sid=r["sid"], side=side, agent=r["agent"], repo=r["repo"], number=r["number"], group=r["group"], majority=r["majority"],
                         outcome=r["outcome"], req_src=r["req_src"], issue=r["issue"], issue_author=r["issue_author"], reviewer=r["reviewer"],
                         reviewer_is_requester=r.get("reviewer_is_requester"), **m, rev_quote=rev))
pd.DataFrame(rows).to_csv(os.path.join(BASE, "upstream_me.csv"), index=False)
print(len(rows))
