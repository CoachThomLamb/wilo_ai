"""Why and when the coach calls tools: per user message, the sequence of tool calls it triggered. Read-only."""
import json, collections
from wilo import data
db = data.connect()
seqs = collections.Counter(); per_msg = collections.Counter(); first_in_chat = collections.Counter()
dry = collections.Counter(); wet = collections.Counter(); schema_before_write = 0; writes = 0
msgs_total = 0
for t in db.collection('chat_threads').stream():
    chat_first = True
    for tu in sorted(t.reference.collection('turns').stream(), key=lambda s: s.id):
        calls = []
        for m in json.loads(tu.to_dict()['messages']):
            if isinstance(m['content'], str): continue
            for b in m['content']:
                if b['type'] == 'tool_use':
                    n = b['name']
                    if n in ('assign_workout', 'update_workout', 'update_profile'):
                        (wet if b['input'].get('write') else dry)[n] += 1
                    calls.append(n)
        msgs_total += 1
        per_msg[len(calls)] += 1
        if calls:
            seqs[' > '.join(calls)] += 1
            if chat_first: first_in_chat[calls[0]] += 1; chat_first = False
print('user messages:', msgs_total, '| tool calls per message:', dict(sorted(per_msg.items())))
print('dry runs:', dict(dry), '| writes:', dict(wet))
print('first tool in a chat:', dict(first_in_chat.most_common()))
print('most common sequences per message:')
for s, c in seqs.most_common(15): print(f'  {c:3}x  {s}')
