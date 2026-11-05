import json, collections
from wilo import data
db = data.connect()
c = collections.Counter(); first = collections.Counter(); chats = 0
for t in db.collection('chat_threads').stream():
    seen = []
    for tu in sorted(t.reference.collection('turns').stream(), key=lambda s: s.id):
        for m in json.loads(tu.to_dict()['messages']):
            if isinstance(m['content'], str): continue
            for b in m['content']:
                if b['type'] == 'tool_use' and b['name'] in ('recent_completed', 'recent_assigned'):
                    c[(b['name'], b['input'].get('limit'))] += 1
                if b['type'] == 'tool_use': seen.append(b['name'])
    if seen: first[seen[0]] += 1; chats += 1
print('limits passed:', dict(c))
print('first tool call in a chat:', dict(first), 'of', chats, 'chats')
