"""Aggregate coded units: CSV export, cross-tables, Cohen's kappa between coder A and coder B.

Usage: python3 aggregate.py <coderAB.jsonl>
Writes units.csv and prints markdown tables (used in results.md).
"""
import json, sys, csv, os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
STAGES = ["1", "2", "3", "4"]
ASSIGN = ["ai_allowed", "human_approval", "ai_forbidden", "human_does"]


def norm(u):
    return {"stage": str(u.get("stage", "")).strip(), "assignee": str(u.get("assignee", "")).strip(),
            "enforceable": str(u.get("enforceable", "")).strip().lower()}


units = []
for r in rows:
    B = r.get("codesB") or []
    for i, u in enumerate(r["units"]):
        a = norm(u)
        b = norm(B[i]) if i < len(B) else None
        units.append({"doc_type": r["doc_type"], "doc_id": r["doc_id"], "quote": u.get("quote", ""), **{k + "_A": v for k, v in a.items()},
                      **({k + "_B": v for k, v in b.items()} if b else {"stage_B": "", "assignee_B": "", "enforceable_B": ""})})

with open(os.path.join(HERE, "units.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(units[0].keys()))
    w.writeheader(); w.writerows(units)


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n / n
    return (po - pe) / (1 - pe) if pe < 1 else 1.0, po, n


def pct(a, b):
    return f"{a} ({100 * a / b:.1f}%)" if b else "0"


docs = Counter(r["doc_type"] for r in rows)
with_units = Counter(r["doc_type"] for r in rows if r["units"])
print("## Documents")
print("| type | documents | with >=1 unit | units | truncated | coder A errors | coder B errors |")
print("|---|---|---|---|---|---|---|")
for t in ["HUMANS.md", "AGENTS.md"]:
    rs = [r for r in rows if r["doc_type"] == t]
    print(f"| {t} | {len(rs)} | {with_units[t]} | {sum(len(r['units']) for r in rs)} | {sum(r['truncated'] for r in rs)} | "
          f"{sum(1 for r in rs if r.get('error'))} | {sum(1 for r in rs if r.get('errorB'))} |")

for scope in ["all", "HUMANS.md", "AGENTS.md"]:
    us = [u for u in units if scope == "all" or u["doc_type"] == scope]
    n = len(us)
    print(f"\n## Coder A, {scope} (n={n})")
    print("| stage | units | human_approval | ai_forbidden | human_does | ai_allowed | enforceable=no |")
    print("|---|---|---|---|---|---|---|")
    for s in STAGES:
        ss = [u for u in us if u["stage_A"] == s]
        c = Counter(u["assignee_A"] for u in ss)
        ne = sum(u["enforceable_A"] == "no" for u in ss)
        print(f"| {s} | {pct(len(ss), n)} | {c['human_approval']} | {c['ai_forbidden']} | {c['human_does']} | {c['ai_allowed']} | {pct(ne, len(ss))} |")
    s23 = [u for u in us if u["stage_A"] in ("2", "3")]
    ne23 = sum(u["enforceable_A"] == "no" for u in s23)
    s4 = [u for u in us if u["stage_A"] == "4"]
    ne4 = sum(u["enforceable_A"] == "no" for u in s4)
    print(f"\nstage 2+3: {pct(len(s23), n)}; of which not enforceable: {pct(ne23, len(s23))}")
    print(f"stage 4: {pct(len(s4), n)}; of which not enforceable: {pct(ne4, len(s4))}")
    docs_with_23 = len({u['doc_id'] for u in s23})
    docs_total = sum(1 for r in rows if (scope == 'all' or r['doc_type'] == scope))
    print(f"documents with >=1 stage 2/3 unit: {pct(docs_with_23, docs_total)}")

pairs = [u for u in units if u["stage_B"]]
print(f"\n## Agreement, coder A vs coder B (units coded by both: {len(pairs)} / {len(units)})")
print("| code | Cohen's kappa | raw agreement | n |")
print("|---|---|---|---|")
for k in ["stage", "assignee", "enforceable"]:
    kp, po, n = kappa([(u[k + "_A"], u[k + "_B"]) for u in pairs])
    print(f"| {k} | {kp:.2f} | {po:.2f} | {n} |")
kp, po, n = kappa([(u["stage_A"] in ("2", "3"), u["stage_B"] in ("2", "3")) for u in pairs])
print(f"| stage 2/3 vs other | {kp:.2f} | {po:.2f} | {n} |")

print("\n## Coder B distribution (robustness)")
for s in STAGES:
    ss = [u for u in pairs if u["stage_B"] == s]
    print(f"stage {s}: {pct(len(ss), len(pairs))}, not enforceable {pct(sum(u['enforceable_B'] == 'no' for u in ss), len(ss))}")
