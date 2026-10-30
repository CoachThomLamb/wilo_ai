"""Print synthetic items as a markdown table for review: python review_table.py 301 > round2-review.md"""
import json
import sys
from pathlib import Path

start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
items = [json.loads(l) for l in open(Path(__file__).resolve().parent.parent / 'train_synth.jsonl')]
esc = lambda s: str(s).replace('|', '/').replace('\n', ' ')
print(f'# Training data from synth-{start:03d}\n\n| # | date | Wilo said | Thom says | label |\n|---|---|---|---|---|')
for i in items:
    n = int(i['id'].split('-')[1])
    if n < start:
        continue
    e, a = i['expected'], dict(i['expected']['args'] or {})
    w = a.pop('workout', None)
    if w:
        a['workout'] = f"{len(w['exercises'])} ex, for {w['assignedFor']}"
    a.pop('collection', None), a.pop('doc_id', None)
    a = {k: (v.splitlines()[-1] if isinstance(v, str) and '\n' in v else v) for k, v in a.items()}
    prev = next((c['text'][:90] for c in reversed(i['context']) if c['role'] == 'assistant'), '')
    call = f"`{e['tool']}({', '.join(f'{k}={v}' for k, v in a.items())})`" if e['tool'] else '**no tool**'
    print(f"| {n} | {i['date'][5:]} | {esc(prev)} | {esc(i['message'])} | {esc(call)} |")
