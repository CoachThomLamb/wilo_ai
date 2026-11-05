import json
from wilo import data
db = data.connect()
rows = []
for t in db.collection('chat_threads').stream():
    d = t.to_dict()
    turns = sorted(t.reference.collection('turns').stream(), key=lambda s: s.id)
    user = asst = tool = think = 0
    msgs = 0
    for tu in turns:
        for m in json.loads(tu.to_dict()['messages']):
            msgs += 1
            c = m['content']
            if isinstance(c, str):
                user += len(c) if m['role'] == 'user' else 0
                continue
            for b in c:
                if b['type'] == 'text': asst += len(b['text'])
                elif b['type'] == 'tool_result': tool += len(json.dumps(b['content']))
                elif b['type'] == 'tool_use': asst += len(json.dumps(b['input']))
                else: think += len(json.dumps(b))
    rows.append((d.get('createdAt','')[:16], d['uid'][:6], len(turns), msgs, len(d.get('context','')), user, asst, tool, think))
rows.sort()
print('created          uid    turns msgs  ctx    user   asst   tool  think  ~tok(total/4)')
for r in rows[-25:]:
    print(*r, (r[4]+r[5]+r[6]+r[7]+r[8])//4)
print(len(rows), 'threads total')
