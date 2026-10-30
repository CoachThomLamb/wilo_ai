"""Talk to Kimi as Wilo: coach.md is its system prompt, and it calls the real WILO tools on your data.

    ~/wilo/.venv/bin/python ml/kimi_coach.py                       # coach.md from ~/wilo/wilo/coach.md
    ~/wilo/.venv/bin/python ml/kimi_coach.py --coach path/to/coach.md --model kimi-k3.1-pro

Kimi runs on RunPod's public endpoint (pay per token, ~1-2 cents a message); the key is RUNPOD_API_KEY, from the
env or ~/wilo/ml/.env. Tools run locally through the wilo
package (same as Claude Code's local `wilo` server, user from config/wilo.json). Reads run straight away; anything
that saves (write=True, todos) asks you y/n first. coach.md is re-read every message, so edit it and keep talking.
/reset clears the conversation, /quit exits.
"""
import argparse
import datetime
import json
import os
import urllib.request
from pathlib import Path

from wilo import mcp_server as tools

HERE = Path(__file__).resolve().parent
URL = 'https://api.runpod.ai/v2/moonshot-kimi/openai/v1/chat/completions'
SAVES = {'add_todo', 'update_todo', 'delete_todo'}  # these save without a write flag
DIM, BOLD, END = '\033[2m', '\033[1m', '\033[0m'


def env_key():
    """RUNPOD_API_KEY from ~/wilo/ml/.env (the main checkout's, gitignored)."""
    f = Path('~/wilo/ml/.env').expanduser()
    for line in f.read_text().splitlines() if f.exists() else []:
        if line.startswith('RUNPOD_API_KEY='):
            return line.split('=', 1)[1].strip().strip('"\'')


def system(coach):
    today = datetime.date.today()
    return f"{Path(coach).expanduser().read_text()}\n\nToday is {today:%A}, {today.isoformat()}."


def chat(key, model, msgs, defs):
    body = {'model': model, 'messages': msgs, 'tools': defs, 'tool_choice': 'auto', 'max_tokens': 4096}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={
        'Content-Type': 'application/json', 'Authorization': f'Bearer {key}', 'User-Agent': 'wilo-ml/1.0'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)['choices'][0]['message']


def run(name, args):
    if name in SAVES or args.get('write') is True or str(args.get('write')).lower() == 'true':
        if input(f'{BOLD}  save? {name} — y/n {END}').strip().lower() != 'y':
            return {'error': 'The user declined this save. Nothing was written.'}
    try:
        return getattr(tools, name)(**args)
    except Exception as e:
        return {'error': f'{type(e).__name__}: {e}'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--coach', default='~/wilo/wilo/coach.md')
    p.add_argument('--model', default='kimi-k3.1-pro')
    a = p.parse_args()
    key = os.environ.get('RUNPOD_API_KEY') or env_key() or exit('Set RUNPOD_API_KEY (or put it in ~/wilo/ml/.env).')
    defs = [t for t in json.loads((HERE / 'wilo_tools.json').read_text()) if t['function']['name'] != 'coaching_method']
    history = []
    while True:
        try:
            text = input('\nyou> ').strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text == '/quit':
            break
        if text == '/reset':
            history = []
            print('(conversation cleared)')
            continue
        if not text:
            continue
        history.append({'role': 'user', 'content': text})
        for _ in range(12):  # tool rounds per message
            msgs = [{'role': 'system', 'content': system(a.coach)}] + history
            try:
                out = chat(key, a.model, msgs, defs)
            except Exception as e:
                print(f'  error: {str(e)[:300]}')
                history.pop()
                break
            calls = out.get('tool_calls') or []
            history.append({k: v for k, v in out.items() if k in ('role', 'content', 'tool_calls', 'reasoning_content') and v is not None})
            if not calls:
                print(f"\nwilo> {out.get('content') or ''}")
                break
            for c in calls:
                name = c['function']['name']
                try:
                    args = json.loads(c['function'].get('arguments') or '{}')
                except ValueError:
                    args = {}
                shown = {k: (f"<workout: {len(v.get('exercises', []))} exercises>" if k == 'workout' and isinstance(v, dict) else v)
                         for k, v in args.items()}
                print(f'{DIM}  → {name}({json.dumps(shown, ensure_ascii=False)[:300]}){END}')
                result = run(name, args)
                history.append({'role': 'tool', 'tool_call_id': c['id'],
                                'content': json.dumps(result, ensure_ascii=False, default=str)})


if __name__ == '__main__':
    main()
