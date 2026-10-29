"""Export coaching from local Claude Code transcripts into the claude.ai trace format.

Each output line: {id, url, title, updated_at, source, messages: [{role, content, tool_calls?}]}.
Coaching = calls to wilo coaching tools. Calls are grouped into clusters (gap > 60 min starts a
new one); each cluster becomes one record holding the messages from 20 min before its first
call to 10 min after its last. Short pure-coaching sessions come out whole.

    python3 coaching-evals/export_claude_code.py <out_claude_code.jsonl> <out_combined.jsonl> <claude_ai_export.jsonl>

Used once on 2026-10-20 to build traces.jsonl (then labeled by hand). To add new chats,
append records to traces.jsonl; never reorder it (notes.json is keyed by message index).
"""
import json, pathlib, sys
from datetime import datetime, timedelta

COACH = {'recent_completed', 'recent_assigned', 'recent_workouts', 'assign_workout', 'update_workout', 'change_workout', 'exercise_history',
         'exercise_names', 'coaching_method', 'get_profile', 'update_profile', 'get_workout', 'workout_schema'}
SKIP = {'281beb48', '5bd22244',   # same conversation as 27adacb4 (resumed copies)
        'de5a2ada'}               # 2026-10-19 data cleanup, not coaching
root = pathlib.Path.home() / '.claude/projects'
out_cc, out_all, claude_ai = map(pathlib.Path, sys.argv[1:4])
ts = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))


def events(f):
    """(time, role, text, tool_calls) per transcript entry; tool results dropped."""
    for line in f.read_text(errors='replace').splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get('type') not in ('user', 'assistant') or not e.get('timestamp') or e.get('isMeta'):
            continue
        c = (e.get('message') or {}).get('content')
        blocks = [{'type': 'text', 'text': c}] if isinstance(c, str) else [b for b in (c or []) if isinstance(b, dict)]
        text = '\n'.join(b.get('text', '') for b in blocks if b.get('type') == 'text').strip()
        calls = [{'name': b['name'].split('__')[-1] if b['name'].startswith('mcp__') else b['name'], 'args': b.get('input')}
                 for b in blocks if b.get('type') == 'tool_use']
        if e['type'] == 'user' and (not text or text.startswith('<')):
            continue   # tool results, command wrappers
        if text or calls:
            yield ts(e['timestamp']), e['type'], text, calls


def merge(evs):
    """Claude Code writes one entry per block; fold consecutive assistant entries into one message."""
    msgs = []
    for t, role, text, calls in evs:
        if msgs and role == 'assistant' and msgs[-1]['role'] == 'assistant':
            m = msgs[-1]
            m['content'] = '\n\n'.join(x for x in (m['content'], text) if x)
            if calls:
                m.setdefault('tool_calls', []).extend(calls)
        else:
            m = {'role': role, 'content': text, 'created_at': t.strftime('%Y-%m-%dT%H:%M:%SZ')}
            if calls:
                m['tool_calls'] = calls
            msgs.append(m)
    return msgs


records = []
for f in sorted(root.rglob('*.jsonl')):
    if 'subagents' in f.parts or f.stem[:8] in SKIP:
        continue
    evs = list(events(f))
    hits = [t for t, _, _, calls in evs if any(c['name'] in COACH for c in calls)]
    if not hits:
        continue
    clusters, cur = [], [hits[0]]
    for t in hits[1:]:
        if t - cur[-1] > timedelta(minutes=60):
            clusters.append(cur); cur = [t]
        else:
            cur.append(t)
    clusters.append(cur)
    whole = len(clusters) == 1 and evs[0][0] >= clusters[0][0] - timedelta(minutes=20) and evs[-1][0] <= clusters[0][-1] + timedelta(minutes=10)
    for i, cl in enumerate(clusters):
        lo, hi = cl[0] - timedelta(minutes=20), cl[-1] + timedelta(minutes=10)
        part = [e for e in evs if lo <= e[0] <= hi]
        msgs = merge(part)
        first_user = next((m['content'] for m in msgs if m['role'] == 'user'), '')
        records.append({
            'id': f'{f.stem}#{i}',
            'url': f'claude-code://{f.parent.name}/{f.stem}',
            'title': first_user.replace('\n', ' ')[:60] or '(no prompt)',
            'updated_at': part[-1][0].strftime('%Y-%m-%dT%H:%M:%SZ'),
            'source': 'claude-code' if whole else 'claude-code-excerpt',
            'messages': msgs,
        })

records.sort(key=lambda r: r['updated_at'])
out_cc.write_text(''.join(json.dumps(r) + '\n' for r in records))
base = [dict(json.loads(l), source='claude.ai') for l in claude_ai.read_text().splitlines() if l.strip()]
out_all.write_text(''.join(json.dumps(r) + '\n' for r in sorted(base + records, key=lambda r: r['updated_at'])))
for r in records:
    calls = [c['name'] for m in r['messages'] for c in m.get('tool_calls', []) if c['name'] in COACH]
    print(f"{r['updated_at'][:16]}  {r['source']:20s} msgs={len(r['messages']):3d} coach_calls={len(calls):2d}  {r['title']}")
print(f'\n{len(records)} Claude Code records; combined file has {len(base) + len(records)}.')
