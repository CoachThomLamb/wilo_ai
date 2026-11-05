"""Cost of the write tools: the workout the coach writes as tool input (generated = output tokens) and the result,
both counted once and counting resends. Read-only."""
import json, collections
from wilo import data
db = data.connect()
inp = collections.Counter(); res = collections.Counter(); n = collections.Counter()
inp_c = collections.Counter(); res_c = collections.Counter(); out_all = 0
for t in db.collection('chat_threads').stream():
    msgs = [m for tu in sorted(t.reference.collection('turns').stream(), key=lambda s: s.id)
            for m in json.loads(tu.to_dict()['messages'])]
    after, k = [], 0
    for m in reversed(msgs): after.append(k); k += m['role'] == 'assistant'
    after.reverse(); names = {}
    for i, m in enumerate(msgs):
        if isinstance(m['content'], str): continue
        for b in m['content']:
            if m['role'] == 'assistant' and b['type'] in ('text', 'tool_use'):
                out_all += len(b.get('text', '')) + len(json.dumps(b.get('input', {})))
            if b['type'] == 'tool_use' and b['name'] in ('update_workout', 'assign_workout'):
                L = len(json.dumps(b['input'])); names[b['id']] = b['name']
                n[b['name']] += 1; inp[b['name']] += L; inp_c[b['name']] += L * after[i]
            elif b['type'] == 'tool_result' and b['tool_use_id'] in names:
                L = len(json.dumps(b['content'])); k2 = names[b['tool_use_id']]
                res[k2] += L; res_c[k2] += L * after[i]
print(f'all visible output (reply text + tool inputs): {out_all//1000}k chars')
for k in n:
    print(f'{k}: {n[k]} calls | input written {inp[k]//1000}k chars (avg {inp[k]//n[k]}), '
          f'{100*inp[k]//out_all}% of visible output | input resent {inp_c[k]//1000}k | result {res[k]//1000}k, resent {res_c[k]//1000}k')
