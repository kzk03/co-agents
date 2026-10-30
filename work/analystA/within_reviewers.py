"""レビュアー固定効果デザインの実現可能性: 同じレビュアーが人間 PR とエージェント PR の両方に CR を出しているか。
(1) within 標本 work/baseline/within/sample.json(群 AG/AO = エージェント, HU/HO = 人間)+ ラベル irr_merged.csv
(2) pilot 全体: work/baseline/within/blocks_agent.jsonl(pilot/raw_full 由来、ボット作者/ボットレビュアー/本文なしを除いた人間 CR 5,918 件)
    + 生データの CHANGES_REQUESTED 件数を pilot/raw_full/*/review_bodies.jsonl から直接数えて照合(読み取りのみ)
実行(humans_md/ で): uv run python work/analystA/within_reviewers.py > work/analystA/within_reviewers.out
"""
import collections, csv, glob, json, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
W = os.path.join(ROOT, "work/baseline/within")
smp = json.load(open(os.path.join(W, "sample.json")))
lab = {r["sid"]: r["majority"] for r in csv.DictReader(open(os.path.join(W, "irr/irr_merged.csv")))}
AG = lambda g: g in ("AG", "AO")
print("== (1) within 標本", len(smp), collections.Counter(s["grp"] for s in smp))
by = collections.defaultdict(lambda: collections.Counter())
for s in smp:
    by[s["reviewer"]]["A" if AG(s["grp"]) else "H"] += 1
both = {r: c for r, c in by.items() if c["A"] and c["H"]}
print(f" レビュアー数 {len(by)}  両方に CR がある人 {len(both)}  その CR 件数 {sum(sum(c.values()) for c in both.values())}")
for r, c in sorted(both.items(), key=lambda x: -sum(x[1].values())):
    items = [(s["sid"], s["grp"], s["repo"], lab.get(s["sid"])) for s in smp if s["reviewer"] == r]
    print("  ", r, dict(c), items)
valid = lambda m: m and m not in ("BOT", "UNK", "NOAGREE")
bv = [r for r in both if any(valid(lab.get(s["sid"])) and AG(s["grp"]) for s in smp if s["reviewer"] == r)
      and any(valid(lab.get(s["sid"])) and not AG(s["grp"]) for s in smp if s["reviewer"] == r)]
print(f" 有効ラベルが両側にある人 {len(bv)}")
# 一致/不一致の組(H/C が人間側とエージェント側で違うか)
for r in bv:
    a = [lab[s["sid"]][0] == "H" for s in smp if s["reviewer"] == r and AG(s["grp"]) and valid(lab.get(s["sid"]))]
    h = [lab[s["sid"]][0] == "H" for s in smp if s["reviewer"] == r and not AG(s["grp"]) and valid(lab.get(s["sid"]))]
    print(f"   {r}: エージェント側 H {sum(a)}/{len(a)} 人間側 H {sum(h)}/{len(h)}")

print("\n== (2) pilot 全体")
RAW = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/pilot_raw_full"))
raw_cr = 0
for f in glob.glob(RAW + "/*/review_bodies.jsonl"):
    for l in open(f):
        try: j = json.loads(l)
        except json.JSONDecodeError: continue
        raw_cr += sum(1 for r in j.get("reviews") or [] if r.get("state") == "CHANGES_REQUESTED")
print(f" 生データの CHANGES_REQUESTED 総数(ボット含む) {raw_cr}")
blocks = [json.loads(l) for l in open(os.path.join(W, "blocks_agent.jsonl"))]
print(" 人間 CR ブロック", len(blocks), collections.Counter(b["agent_level"] for b in blocks))
for agent_def, nm in ((("strong",), "strong のみ"), (("strong", "weak"), "strong+weak")):
    for scope in ("全 repo 通算", "同一 repo 内"):
        key = (lambda b: b["reviewer"]) if scope == "全 repo 通算" else (lambda b: (b["repo"], b["reviewer"]))
        c = collections.defaultdict(lambda: collections.Counter())
        for b in blocks:
            if b["agent_level"] in agent_def: c[key(b)]["A"] += 1
            elif b["agent_level"] == "none": c[key(b)]["H"] += 1
        bo = {k: v for k, v in c.items() if v["A"] and v["H"]}
        nA = sum(v["A"] for v in bo.values()); nH = sum(v["H"] for v in bo.values())
        allA = sum(v["A"] for v in c.values())
        k2 = sum(1 for v in bo.values() if v["A"] >= 2 and v["H"] >= 2)
        print(f" [{nm} / {scope}] 両方ある単位 {len(bo)}(全 {len(c)})  その CR: エージェント {nA}/{allA} 件, 人間 {nH} 件 | 両側2件以上 {k2}")
        if scope == "同一 repo 内":
            rc = collections.Counter(k[0] for k in bo)
            print("   repo 別(単位数):", rc.most_common(10))
            print("   上位(エージェント件数順):", sorted(((k[1], k[0], v["A"], v["H"]) for k, v in bo.items()), key=lambda x: -x[2])[:10])

print("\n== strong / 同一 repo 内の重なりのうち home-assistant/core の比重")
c = collections.defaultdict(lambda: collections.Counter())
for b in blocks:
    if b["agent_level"] == "strong": c[(b["repo"], b["reviewer"])]["A"] += 1
    elif b["agent_level"] == "none": c[(b["repo"], b["reviewer"])]["H"] += 1
bo = {k: v for k, v in c.items() if v["A"] and v["H"]}
A = sum(v["A"] for v in bo.values()); ha = sum(v["A"] for k, v in bo.items() if k[0] == "home-assistant/core")
print(f" エージェント側 CR {A} 件のうち HA {ha} ({ha/A:.3f}); 非 HA の単位 {sum(k[0] != 'home-assistant/core' for k in bo)}、"
      f"非 HA エージェント CR {A-ha}、非 HA で両側2件以上 {sum(k[0] != 'home-assistant/core' and v['A'] >= 2 and v['H'] >= 2 for k, v in bo.items())}")
