# pilot 39 repo の AI レビュアーアカウント別 review state 集計(理論担当、読み取りのみ)
import json, glob, collections, os
AI = ('copilot-pull-request-reviewer', 'gemini-code-assist', 'copilot-swe-agent')
c = collections.Counter(); hum = collections.Counter()
for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../data/pilot_raw_full/*/review_bodies.jsonl')):
    for l in open(f):
        r = json.loads(l)
        for rv in r.get('reviews', []):
            a = rv.get('author') or {}
            login = a.get('login') if isinstance(a, dict) else str(a)
            if login in AI: c[(login, rv.get('state'))] += 1
            elif login and 'bot' not in login.lower(): hum[rv.get('state')] += 1
for k, v in sorted(c.items()): print(k, v)
print('non-AI, non-*bot* accounts:', dict(hum))
