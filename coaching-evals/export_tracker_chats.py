"""Export tracker chats (#105) from Firestore into the viewer's trace format (#112).

    .venv/bin/python coaching-evals/export_tracker_chats.py               # dry run: count chats, write nothing
    .venv/bin/python coaching-evals/export_tracker_chats.py --write       # write coaching-evals/tracker_traces.jsonl
    .venv/bin/python coaching-evals/export_tracker_chats.py --uid <uid>[,<uid>]   # other users' chats (needs their OK, #52)

Firestore (chat_threads) is the source; the output is a local, gitignored copy, regenerated whenever needed. Reads
through the read-only facade wilo.data.chat_traces with the admin key. Default uid: config/wilo.json (Thom).

Each line: {id, title, updated_at, source: "tracker", label, uid, context, messages: [{role, content, created_at,
tool_calls?}]}. One user message, then one assistant message holding the whole reply (tool calls folded in, tool
results and thinking dropped), so message indexes stay stable as chats grow and notes.json keeps pointing at the
right reply.
"""
import argparse
import json
from pathlib import Path

from wilo import data as wilo_data

OUT = Path(__file__).resolve().parent / 'tracker_traces.jsonl'


def to_trace(thread):
    msgs = []
    for turn in thread['turns']:
        for m in turn['messages']:
            content = m['content']
            if m['role'] == 'user':
                if isinstance(content, str):  # what the user typed; lists are tool results
                    msgs.append({'role': 'user', 'content': content, 'created_at': turn['at']})
                continue
            text = '\n\n'.join(b['text'] for b in content if b.get('type') == 'text' and b.get('text')).strip()
            calls = [{'name': b['name'], 'args': b.get('input')} for b in content if b.get('type') == 'tool_use']
            if msgs and msgs[-1]['role'] == 'assistant':  # the same reply, continued after a tool call
                last = msgs[-1]
                last['content'] = '\n\n'.join(x for x in (last['content'], text) if x)
                if calls:
                    last.setdefault('tool_calls', []).extend(calls)
            else:
                msg = {'role': 'assistant', 'content': text, 'created_at': turn['at']}
                if calls:
                    msg['tool_calls'] = calls
                msgs.append(msg)
    first = next((m['content'] for m in msgs if m['role'] == 'user'), '')
    return {'id': thread['chatId'], 'title': first[:60] or '(empty chat)',
            'updated_at': (thread['turns'][-1]['at'] if thread['turns'] else thread['createdAt']),
            'source': 'tracker', 'label': 'coaching', 'uid': thread['uid'], 'context': thread['context'],
            'messages': msgs}


def main(argv=None):
    p = argparse.ArgumentParser(description='Export tracker chats from Firestore for the coaching-evals viewer.')
    p.add_argument('--uid', default=wilo_data.CONFIG['uid'], help="whose chats, comma-separated (default: config/wilo.json)")
    p.add_argument('--write', action='store_true', help=f'write {OUT.name} (default: dry run)')
    args = p.parse_args(argv)

    db = wilo_data.connect()
    uids = [u.strip() for u in args.uid.split(',') if u.strip()]
    threads = sorted((t for u in uids for t in wilo_data.chat_traces(db, uid=u)), key=lambda t: (t['createdAt'] or '', t['chatId']))
    traces = [to_trace(t) for t in threads]
    n = sum(len(t['messages']) for t in traces)
    span = f", {traces[0]['updated_at'][:10]} to {traces[-1]['updated_at'][:10]}" if traces else ''
    print(f'{len(traces)} chats, {n} messages for {args.uid}{span}')
    if not args.write:
        print(f'Dry run: nothing written. Add --write to save {OUT}.')
        return
    OUT.write_text(''.join(json.dumps(t, ensure_ascii=False) + '\n' for t in traces))
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
