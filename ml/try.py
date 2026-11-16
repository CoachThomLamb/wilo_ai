"""Talk to the base and the fine-tuned model side by side and see which tool each would call.

    python ml/try.py --pod <podId> --key <VLLM_KEY>
    python ml/try.py --pod <podId> --key <VLLM_KEY> --screen <assignedDocId>   # as if that workout is loaded

Type a message the way you would to Wilo. Each model gets the same prompt score.py uses (with the earlier turns), and
you see the tool call it picked. Nothing runs: the tools are only definitions. /reset clears the conversation.
"""
import argparse
import json
from pathlib import Path

from score import ask

HERE = Path(__file__).resolve().parent
MODELS = [('base', 8001, 'Qwen/Qwen3.5-4B'), ('wilo-ft', 8000, 'wilo-ft')]


def show(got):
    if got['tool'] is None:
        return f"no tool: {got.get('text', '').strip()[:200]}"
    return f"{got['tool']}({json.dumps(got.get('args') or {}, ensure_ascii=False)[:400]})"


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--pod', required=True), p.add_argument('--key', required=True)
    p.add_argument('--screen', help='assignedDocId of the workout on screen')
    a = p.parse_args()
    tools = json.loads((HERE / 'wilo_tools.json').read_text())
    screen = {'name': None, 'assignedDocId': a.screen} if a.screen else None
    context = []
    while True:
        try:
            msg = input('\nyou> ').strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg == '/reset':
            context = []
            print('(conversation cleared)')
            continue
        if not msg:
            continue
        item = {'context': context, 'message': msg, 'screen': screen}
        picks = {}
        for name, port, model in MODELS:
            try:
                got, secs = ask(f'https://{a.pod}-{port}.proxy.runpod.net/v1', a.key, model, item, tools)
                picks[name] = got
                print(f'  {name:8} {secs:4.1f}s  {show(got)}')
            except Exception as e:
                print(f'  {name:8} error: {str(e)[:200]}')
        # Earlier turns, as the fine-tuned model saw them: what you said and the tool it picked.
        ft = picks.get('wilo-ft') or {'tool': None}
        context = (context + [{'role': 'user', 'text': msg},
                              {'role': 'assistant', 'text': '', 'tools': [ft['tool']] if ft['tool'] else []}])[-8:]


if __name__ == '__main__':
    main()
