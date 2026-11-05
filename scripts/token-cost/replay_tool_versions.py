"""Read-only replay of every stored coach chat under three tool versions, on today's data:
  original = the tool results actually stored in the chat (pre-#144 code, data as it was then)
  #144     = main's code just before #146 (trimmed reads, summaries), against assigned/completed
  #146     = today's code (one doc per workout), against workouts
Text, thinking and the user's messages are kept as they were; only tool payloads change.
  lean     = #146 plus training_summary / current_workout in place of the two list reads
Input = every message's size x the API calls that resend it. Output = what the coach generated (counted once).

    git show f314870:wilo/data.py > /tmp/old144_data.py
    .venv/bin/python scripts/token-cost/replay_tool_versions.py /tmp/old144_data.py"""
import json, re, sys, collections, statistics, importlib.util
sys.path.insert(0, '/home/thom/wilo')
from wilo import data as new
spec = importlib.util.spec_from_file_location('old144', sys.argv[1]); old = importlib.util.module_from_spec(spec)
old.__file__ = '/home/thom/wilo/wilo/old144.py'   # so it finds config/ and schema/ like the real one
spec.loader.exec_module(old)
db = new.connect()
J = lambda x: len(json.dumps(x, default=str))
cache = {}
def obj(x):
    if isinstance(x, str):
        try: return json.loads(x)
        except Exception: return {}
    return x if isinstance(x, dict) else {}
def memo(key, fn):
    if key not in cache: cache[key] = fn()
    return cache[key]

def full_docs(uid):   # whole workout docs (what get_workout returns now)
    return memo(('full', uid), lambda: [{'docId': d.id, **d.to_dict()} for d in new.collection(db, uid, 'workouts').stream()])

def sizes(name, inp, stored_result, uid):
    """(input chars the coach wrote, result chars) for each version: original, #144, #146."""
    lim = inp.get('limit', 5)
    orig = (J(inp), stored_result)
    if name == 'recent_completed':
        r144 = memo(('c144', uid, lim), lambda: J({'workouts': [old.slim(w) for w in old.recent(db, uid, 'completed', min(lim, old.MAX_LIST))]}))
        r146 = memo(('d146', uid, lim), lambda: J({'workouts': new.recent(db, uid, 'done', lim)}))
        rl = memo(('sum', uid), lambda: J({'summary': new.summary(db, uid, '2026-11-05', 14)}))
        return orig, (J(inp), r144), (J({'status': 'done', 'limit': lim}), r146), (J({'days': 14}), rl)
    if name == 'recent_assigned':
        r144 = memo(('a144', uid, lim), lambda: J({'workouts': old.upcoming(db, uid, min(lim, old.MAX_LIST))}))
        r146 = memo(('p146', uid, lim), lambda: J({'workouts': new.recent(db, uid, 'planned', lim)}))
        rl = memo(('cur', uid), lambda: sum(J({'workout': new.current(db, uid, f'2026-11-{d:02d}')}) for d in range(5, 12)) // 7)
        return orig, (J(inp), r144), (J({'status': 'planned', 'limit': lim}), r146), (2, rl)
    if name == 'get_workout':   # whole doc in every version; now plan + diffs + exercises + log
        docs = full_docs(uid); avg = sum(map(J, docs)) // max(len(docs), 1)
        return orig, orig, (J({'doc_id': inp.get('doc_id', '')}), avg), (J({'doc_id': inp.get('doc_id', '')}), avg)
    if name == 'update_workout':
        w = obj(inp.get('workout')); exs = w.get('exercises') or []
        res = stored_full.get('res') or {}
        changes = res.get('changes') or []
        r144 = J({**{k: v for k, v in res.items() if k != 'changes'}, 'changes': changes[:20], **({'moreChanges': len(changes) - 20} if len(changes) > 20 else {})}) if res else stored_result
        touched = sorted({int(m.group(1)) for c in changes for m in [re.match(r'exercises/(\d+)', c)] if m})
        ops = [{'op': 'set', 'exId': f'x{i+1}', 'fields': {k: v for k, v in exs[i].items() if k not in ('instanceId', 'exId', 'fallback')}}
               for i in touched if i < len(exs)] or [{'op': 'workout', 'name': w.get('name', '')}]
        outline = [{'exId': f'x{i+1}', 'name': x.get('name', ''), 'sets': len(x.get('sets', []) or [])} for i, x in enumerate(exs)]
        r146 = J({'ok': True, 'path': 'users/u/workouts/d', 'exercises': outline})
        c146 = (J({'doc_id': inp.get('doc_id', ''), 'ops': ops, 'write': inp.get('write', False)}), r146)
        return orig, (J(inp), r144), c146, c146
    if name == 'assign_workout':
        w = obj(inp.get('workout')); exs = w.get('exercises') or []
        r144 = J({'ok': True, 'path': 'users/u/assigned/d', 'id': w.get('id'), 'name': w.get('name'), 'assignedFor': w.get('assignedFor'), 'exercises': len(exs)})
        r146 = J({'ok': True, 'path': 'users/u/workouts/d', 'docId': 'd', 'name': w.get('name'), 'assignedFor': w.get('assignedFor'),
                  'exercises': [{'exId': f'x{i+1}', 'name': x.get('name', ''), 'sets': len(x.get('sets', []) or [])} for i, x in enumerate(exs)]})
        return orig, (J(inp), r144), (J(inp), r146), (J(inp), r146)
    return orig, orig, orig, orig

stored_full = {}
V = ('original', '#144', '#146', 'lean')
tot_in = collections.Counter(); tot_out = collections.Counter(); by_tool = collections.defaultdict(collections.Counter)
per_thread = {v: [] for v in V}; n_user = 0; n_threads = 0
for t in db.collection('chat_threads').stream():
    d = t.to_dict(); uid = d['uid']; n_threads += 1
    msgs = [m for tu in sorted(t.reference.collection('turns').stream(), key=lambda s: s.id) for m in json.loads(tu.to_dict()['messages'])]
    after = []; k = 0
    for m in reversed(msgs):
        after.append(k); k += m['role'] == 'assistant'
    after.reverse()
    uses = {}
    for m in msgs:   # tool_use id -> (name, input)
        if not isinstance(m['content'], str):
            for b in m['content']:
                if b['type'] == 'tool_use': uses[b['id']] = (b['name'], b['input'])
    th_in = collections.Counter()
    for i, m in enumerate(msgs):
        c = m['content']
        n_user += m['role'] == 'user' and isinstance(c, str)
        if isinstance(c, str):
            for v in V: th_in[v] += len(c) * after[i]
            if m['role'] == 'assistant':
                for v in V: tot_out[v] += len(c)
            continue
        for b in c:
            if b['type'] == 'tool_use':
                continue   # counted with its result below, so every version swaps the input too
            if b['type'] == 'tool_result':
                name, inp = uses.get(b['tool_use_id'], ('?', {}))
                stored = J(b['content'])
                try:
                    txt = b['content'] if isinstance(b['content'], str) else ''.join(x.get('text', '') for x in b['content'] if isinstance(x, dict))
                    stored_full['res'] = json.loads(txt)
                except Exception:
                    stored_full['res'] = None
                vs = sizes(name, inp, stored, uid)
                # where the tool_use sat: one message earlier (the assistant turn)
                use_after = after[i - 1] if i else after[i]
                for v, (si, sr) in zip(V, vs):
                    th_in[v] += si * use_after + sr * after[i]
                    tot_out[v] += si
                    by_tool[name][v] += si * use_after + sr * after[i]
            else:   # text, thinking: unchanged
                s = J(b)
                for v in V: th_in[v] += s * after[i]
                if m['role'] == 'assistant':
                    for v in V: tot_out[v] += s
    for v in V:
        tot_in[v] += th_in[v]; per_thread[v].append(th_in[v])
stored_full = {}
print(f'{n_threads} chats, {n_user} user messages. Chars; ~4 chars per token.')
print(f'{"":10}{"input (resends)":>18}{"per message":>13}{"median chat":>13}{"output":>10}')
for v in V:
    print(f'{v:10}{tot_in[v]//1000:>16}k{tot_in[v]//n_user//1000:>12}k{int(statistics.median(per_thread[v]))//1000:>12}k{tot_out[v]//1000:>9}k')
print('\ninput carried by tool (chars, incl. resends):')
print(f'{"tool":18}' + ''.join(f'{v:>12}' for v in V))
for name, c in sorted(by_tool.items(), key=lambda kv: -kv[1]['original'])[:9]:
    print(f'{name:18}' + ''.join(f'{c[v]//1000:>11}k' for v in V))
