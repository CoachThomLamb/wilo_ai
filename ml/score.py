"""Score a model on the tool-calling eval (ml/toolcall_eval.jsonl) through any OpenAI-compatible endpoint.

    python ml/score.py                                  # the RunPod pod in ml/.pod.json
    python ml/score.py --url http://localhost:11434/v1 --model qwen3.5:4b   # Ollama on the Mac
    python ml/score.py --limit 10                       # a quick check first

The task: given a real message (and a few earlier messages), call the WILO tool Claude called, or answer without a
tool when Claude did. Writes per-item results to ml/results/<model>-<time>.jsonl and prints the summary.
Read-only for WILO: the model only sees tool definitions, nothing runs against real data.
"""
import argparse
import json
import re
import time
import urllib.request
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYSTEM = """You are the tool-calling part of Wilo, a workout coach in a phone app. Read the user's latest message
(with the conversation before it) and either call the one WILO tool that should run next, with the right arguments,
or reply in one short sentence if no tool is needed. Messages are often messy voice-to-text."""


def ask(url, key, model, item, tools):
    msgs = [{'role': 'system', 'content': SYSTEM}]
    for c in item['context']:
        text = c['text'] + (f"\n[called: {', '.join(c['tools'])}]" if c.get('tools') else '')
        msgs.append({'role': 'user' if c['role'] == 'user' else 'assistant', 'content': text or '(no text)'})
    # Like the app since #124: the user's message starts with which workout is on screen.
    scr = item.get('screen')
    line = (f'[Tracker: "{scr["name"] or "workout"}" on screen; the plan: get_workout(\'assigned\', \'{scr["assignedDocId"]}\')]'
            if scr else '[Tracker: no workout loaded]')
    msgs.append({'role': 'user', 'content': f"{line}\n{item['message']}"})
    body = {'model': model, 'messages': msgs, 'tools': tools, 'tool_choice': 'auto', 'max_tokens': 4096, 'temperature': 0}
    req = urllib.request.Request(url + '/chat/completions', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {key}',
                                          'User-Agent': 'wilo-ml/1.0'})  # RunPod's proxy 403s Python's default
    t = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.load(r)['choices'][0]['message']
    calls = out.get('tool_calls') or []
    if not calls:
        return {'tool': None, 'text': out.get('content') or ''}, time.time() - t
    fn = calls[0]['function']
    try:
        args = json.loads(fn.get('arguments') or '{}')
    except ValueError:
        args = {'_unparsed': fn.get('arguments')}
    return {'tool': fn['name'], 'args': args}, time.time() - t


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', str(s).lower()).strip()


def args_ok(tool, want, got, complete=True):
    """Do the arguments that matter match? Free text is compared loosely; big workout objects only for shape.
    complete=False (the label kept only a summary): only the doc and the write flag are compared."""
    if '_unparsed' in got:
        return False
    if not complete:
        return got.get('doc_id') == want.get('doc_id') and bool(got.get('write')) == bool(want.get('write'))
    if tool == 'get_workout':
        return got.get('collection') == want.get('collection') and got.get('doc_id') == want.get('doc_id')
    if tool == 'exercise_history':
        w, g = norm(want.get('name', '')), norm(got.get('name', ''))
        return bool(g) and (w in g or g in w)
    if tool in ('assign_workout', 'update_workout'):
        wk = got.get('workout')
        same_doc = tool == 'assign_workout' or got.get('doc_id') == want.get('doc_id')
        shape = isinstance(wk, dict) and isinstance(wk.get('exercises'), list) and len(wk['exercises']) > 0
        return same_doc and shape and bool(got.get('write')) == bool(want.get('write'))
    if tool == 'update_profile':
        keys = lambda d: {k for k in d if k != 'write'}
        return keys(got) == keys(want) and bool(got.get('write')) == bool(want.get('write'))
    if tool == 'add_todo':
        return bool(norm(got.get('text', '')))
    return True  # reads with optional args (recent_completed, recent_assigned, exercise_names, ...)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--url'), p.add_argument('--key', default='none'), p.add_argument('--model')
    p.add_argument('--eval', default=str(HERE / 'toolcall_eval.jsonl'))
    p.add_argument('--limit', type=int)
    a = p.parse_args()
    if not a.url:
        pod = json.loads((HERE / '.pod.json').read_text())
        a.url, a.key, a.model = pod['url'], pod['key'], a.model or pod['model']
    tools = json.loads((HERE / 'wilo_tools.json').read_text())
    items = [json.loads(l) for l in open(a.eval)][:a.limit]

    out_dir = HERE / 'results'
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{re.sub(r'[^A-Za-z0-9.]+', '-', a.model)}-{time.strftime('%Y%m%d-%H%M')}.jsonl"
    per_tool, tool_hits, arg_hits, secs = Counter(), Counter(), Counter(), []
    with open(out_path, 'w') as f:
        for i, item in enumerate(items, 1):
            want = item['expected']
            try:
                got, s = ask(a.url, a.key, a.model, item, tools)
            except Exception as e:
                got, s = {'tool': '_error', 'error': str(e)[:200]}, 0
            secs.append(s)
            t_ok = got['tool'] == want['tool']
            a_ok = t_ok and (want['tool'] is None or args_ok(want['tool'], want.get('args') or {}, got.get('args') or {},
                                                                          want.get('args_complete', True)))
            name = want['tool'] or 'none'
            per_tool[name] += 1
            tool_hits[name] += t_ok
            arg_hits[name] += a_ok
            f.write(json.dumps({'id': item['id'], 'want': want, 'got': got, 'tool_ok': t_ok, 'args_ok': a_ok,
                                'secs': round(s, 1)}, ensure_ascii=False) + '\n')
            print(f"{i:3}/{len(items)} {'✓' if a_ok else ('~' if t_ok else '✗')} want {name:16} got {got['tool']}", flush=True)

    n = len(items)
    print(f"\n{a.model}: right tool {sum(tool_hits.values())}/{n} ({100*sum(tool_hits.values())//n}%), "
          f"right tool + args {sum(arg_hits.values())}/{n} ({100*sum(arg_hits.values())//n}%), "
          f"median {sorted(secs)[len(secs)//2]:.1f}s per item")
    for name, k in per_tool.most_common():
        print(f"  {name:18} tool {tool_hits[name]}/{k}  args {arg_hits[name]}/{k}")
    print(f'details: {out_path}')


if __name__ == '__main__':
    main()
