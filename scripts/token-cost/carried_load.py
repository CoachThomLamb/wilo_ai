"""Tool-result cost including resends: chars x (API calls that carry it). Read-only.
An API call = each assistant message (one per tool step). A tool result is sent on every later call in its chat."""
import json, collections
from wilo import data
db = data.connect()
load = collections.Counter(); once = collections.Counter(); n = collections.Counter(); total = 0
for t in db.collection('chat_threads').stream():
    msgs = [m for tu in sorted(t.reference.collection('turns').stream(), key=lambda s: s.id)
            for m in json.loads(tu.to_dict()['messages'])]
    calls_after = []  # for each message index: number of assistant messages after it
    k = 0
    for m in reversed(msgs):
        calls_after.append(k); k += m['role'] == 'assistant'
    calls_after.reverse()
    names = {}
    for i, m in enumerate(msgs):
        c = m['content']
        size = len(c) if isinstance(c, str) else len(json.dumps(c))
        total += size * calls_after[i]
        if isinstance(c, str): continue
        for b in c:
            if b['type'] == 'tool_use':
                lim = b['input'].get('limit')
                names[b['id']] = b['name'] + (f' lim={"1" if lim == 1 else "2-3" if lim and lim <= 3 else "5+"}' if b['name'].startswith('recent') else '')
            elif b['type'] == 'tool_result':
                key = names.get(b['tool_use_id'], '?'); L = len(json.dumps(b['content']))
                n[key] += 1; once[key] += L; load[key] += L * calls_after[i]
print(f'all history resent, total: {total//1000}k chars (~{total//4000}k tokens)')
print(f'{"tool":28} calls  once   carried  %of-all')
for key, v in load.most_common(12):
    print(f'{key:28} {n[key]:5} {once[key]//1000:4}k {v//1000:7}k  {100*v//total:3}%')
