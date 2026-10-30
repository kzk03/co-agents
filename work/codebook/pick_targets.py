import csv, json, re
out = []
for name in ['aidev', 'ghhuman']:
    rows = {r['sid']: r for r in csv.DictReader(open(f'outputs/{name}/irr/irr_merged.csv'))}
    txt = open(f'outputs/{name}/dump.txt').read()
    blocks = {m.group(1): m.group(0) for m in re.finditer(r'### (\w+) .*?(?=\n### |\Z)', txt, re.S)}
    for sid, r in rows.items():
        if r['majority'].startswith('H') or r['majority'] == 'NOAGREE':
            out.append(dict(set=name, sid=sid, v0=r['majority'], me=r['me_cat'], son=r['sonnet_cat'], hai=r['haiku_cat'], inf=r['majority_inf'], text=blocks[sid].strip()))
json.dump(out, open('work/codebook/targets.json', 'w'), ensure_ascii=False, indent=1)
with open('work/codebook/targets_dump.txt', 'w') as f:
    for o in out:
        f.write(f"[{o['v0']} me={o['me']} son={o['son']} hai={o['hai']} inf={o['inf']}]\n{o['text']}\n\n")
print(len(out), sum(o['set']=='aidev' for o in out))
