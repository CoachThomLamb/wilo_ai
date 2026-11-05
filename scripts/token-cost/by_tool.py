import json, collections
from wilo import data
db = data.connect()
n = collections.Counter(); size = collections.Counter(); mx = collections.Counter()
for t in db.collection('chat_threads').stream():
    names = {}
    for tu in sorted(t.reference.collection('turns').stream(), key=lambda s: s.id):
        for m in json.loads(tu.to_dict()['messages']):
            if isinstance(m['content'], str): continue
            for b in m['content']:
                if b['type'] == 'tool_use': names[b['id']] = b['name']
                elif b['type'] == 'tool_result':
                    k = names.get(b['tool_use_id'], '?'); L = len(json.dumps(b['content']))
                    n[k] += 1; size[k] += L; mx[k] = max(mx[k], L)
print('tool               calls  total_chars  avg   max')
for k, _ in size.most_common():
    print(f'{k:18} {n[k]:5} {size[k]:11} {size[k]//n[k]:6} {mx[k]:6}')
