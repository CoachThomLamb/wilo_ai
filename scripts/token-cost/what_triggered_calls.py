import json
from wilo import data
db = data.connect()
for t in sorted(db.collection('chat_threads').stream(), key=lambda s: s.to_dict().get('createdAt','')):
    last = None
    for tu in sorted(t.reference.collection('turns').stream(), key=lambda s: s.id):
        for m in json.loads(tu.to_dict()['messages']):
            if isinstance(m['content'], str): last = m['content']; continue
            for b in m['content']:
                if b['type'] == 'tool_use' and b['name'] in ('recent_completed','recent_assigned'):
                    print(f"{t.to_dict()['createdAt'][:10]} {b['name'][7:]:9} lim={b['input'].get('limit')}  <- {last[:110]!r}")
                    last = '(same msg)'
