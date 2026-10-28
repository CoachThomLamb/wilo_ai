"""Build the tool-calling eval set for the small-model experiment (ml/README.md).

Each item: a real user message (with a few messages of context) and the first WILO tool Claude called in reply,
or "none" when Claude answered without a tool. Claude's choice is a silver label: Thom reviews it (`review`).

    python3 ml/build_eval.py --tracker coaching-evals/tracker_traces.jsonl --uid <Thom's uid> > ml/toolcall_eval.jsonl

Sources: coaching-evals/traces.jsonl (claude.ai + Claude Code chats, committed) and the tracker-chat export
(coaching-evals/export_tracker_chats.py; local, gitignored). Only Thom's chats (--uid): other users' messages
don't go into the repo (#52).
"""
import argparse
import json
import re
import sys

WILO_TOOLS = {'coaching_method', 'get_profile', 'update_profile', 'workout_schema', 'recent_completed',
              'recent_assigned', 'get_workout', 'exercise_history', 'exercise_names', 'assign_workout',
              'update_workout', 'add_todo', 'list_todos', 'update_todo', 'delete_todo'}
CONTEXT = 6          # earlier messages kept with each item
MAX_NONE = 20        # "no tool" examples kept (spread evenly), so the set isn't mostly chit-chat


def tool_name(raw):
    """'wilo:assign_workout', 'mcp__claude_ai_wilo__assign_workout' -> 'assign_workout'; other tools -> None."""
    name = re.split(r'[:]|__', raw)[-1]
    return name if name in WILO_TOOLS else None


def complete(name, args):
    """False when the export kept only a summary (old claude.ai export: "note": "same as dry run", no exercises):
    then only the tool, doc and write flag can be scored."""
    if name in ('assign_workout', 'update_workout'):
        return isinstance((args.get('workout') or {}).get('exercises'), list)
    if name == 'add_todo':
        return 'text' in args
    return True


def items(chat, source):
    msgs = chat['messages']
    if source != 'tracker' and not any(tool_name(c['name']) for m in msgs for c in m.get('tool_calls') or []):
        return  # a chat that never touched WILO isn't coaching data
    for i, m in enumerate(msgs):
        if m['role'] != 'user' or i + 1 >= len(msgs) or msgs[i + 1]['role'] != 'assistant':
            continue
        calls = msgs[i + 1].get('tool_calls') or []
        if calls:
            name = tool_name(calls[0]['name'])
            if not name:
                continue  # Claude reached for a non-WILO tool first (Bash, search): not this task
            args = calls[0].get('args') or {}
            expected = {'tool': name, 'args': args, 'args_complete': complete(name, args)}
        elif source.startswith('claude-code'):
            continue  # Claude Code chats mix in dev talk ("can I pause this session"): only their tool calls count
        else:
            expected = {'tool': None}
        context = [{'role': c['role'], 'text': (c.get('content') or '')[:1500],
                    **({'tools': [t['name'] for t in c['tool_calls']]} if c.get('tool_calls') else {})}
                   for c in msgs[max(0, i - CONTEXT):i]]
        yield {'id': f"{chat['id']}#{i}", 'source': source, 'date': (m.get('created_at') or chat.get('updated_at') or '')[:10],
               'context': context, 'message': m.get('content') or '', 'expected': expected, 'review': ''}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--traces', default='coaching-evals/traces.jsonl')
    p.add_argument('--tracker', help='tracker-chat export (local)')
    p.add_argument('--uid', required=True, help="Thom's uid: only his tracker chats are used")
    args = p.parse_args()

    out = []
    for line in open(args.traces):
        chat = json.loads(line)
        out += items(chat, chat.get('source', 'claude.ai'))
    if args.tracker:
        for line in open(args.tracker):
            chat = json.loads(line)
            if chat.get('uid') == args.uid:
                out += items(chat, 'tracker')

    tools = [x for x in out if x['expected']['tool']]
    none = [x for x in out if not x['expected']['tool']]
    step = max(1, len(none) // MAX_NONE)
    final = sorted(tools + none[::step][:MAX_NONE], key=lambda x: (x['date'], x['id']))
    for x in final:
        print(json.dumps(x, ensure_ascii=False))
    counts = {}
    for x in final:
        counts[x['expected']['tool'] or 'none'] = counts.get(x['expected']['tool'] or 'none', 0) + 1
    print(f'{len(final)} items ({len(tools)} tool calls, {min(len(none), MAX_NONE)} of {len(none)} no-tool): '
          f'{dict(sorted(counts.items(), key=lambda kv: -kv[1]))}', file=sys.stderr)


if __name__ == '__main__':
    main()
