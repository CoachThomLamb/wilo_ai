"""Real coach-chat cost from the usage the server saves on every request (#143). Read-only.

    .venv/bin/python scripts/token-cost/usage_report.py [--since 2026-11-05] [--chats 10]

Reads chat_threads/{chatId}/usage/{at} (written by wilo/chat.py since this script was added). Tokens are what the
API reported; dollars use the prices below (per million tokens; update them if Anthropic's change).
"""
import argparse
import collections
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from wilo import data  # noqa: E402

TZ = ZoneInfo('America/Toronto')
# $ per million tokens: input, output, cache read, cache write 5 min (1.25x input), cache write 1 hour (2x input)
PRICES = {'claude-sonnet-5-5': (2.00, 10.00, 0.20, 2.50, 4.00),
          'claude-opus-5-5': (4.00, 20.00, 0.20, 5.00, 8.00)}
KINDS = ('in', 'read', 'write', 'out')


def tokens(u):
    """(in, read, write 5 min, write 1 hour, out) from one call's usage."""
    write = u.get('cache_creation_input_tokens') or 0
    split = u.get('cache_creation') or {}
    w5, w1 = split.get('ephemeral_5m_input_tokens'), split.get('ephemeral_1h_input_tokens')
    if w5 is None and w1 is None:
        w5, w1 = 0, write  # no split reported: the chat caches for 1 hour
    return u.get('input_tokens') or 0, u.get('cache_read_input_tokens') or 0, w5 or 0, w1 or 0, u.get('output_tokens') or 0


def dollars(model, t):
    p = next((v for k, v in PRICES.items() if model.startswith(k)), None)
    if p is None:
        return None
    i, r, w5, w1, o = t
    return (i * p[0] + o * p[1] + r * p[2] + w5 * p[3] + w1 * p[4]) / 1e6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since', help='YYYY-MM-DD, local day')
    ap.add_argument('--chats', type=int, default=10, help='how many of the costliest chats to list')
    a = ap.parse_args()
    db = data.connect()
    day = collections.defaultdict(lambda: collections.Counter())
    chats = collections.defaultdict(lambda: collections.Counter())
    unpriced = set()
    for t in db.collection('chat_threads').stream():
        for u in t.reference.collection('usage').stream():
            d = u.to_dict()
            local = datetime.fromisoformat(d['at']).astimezone(TZ).date().isoformat()
            if a.since and local < a.since:
                continue
            for key, bucket in ((local, day), (t.id, chats)):
                bucket[key]['requests'] += 1
            for c in d.get('calls', []):
                tk = tokens(c.get('usage', {}))
                cost = dollars(c.get('model', ''), tk)
                if cost is None:
                    unpriced.add(c.get('model'))
                    cost = 0
                for bucket in (day[local], chats[t.id]):
                    bucket['calls'] += 1
                    bucket['in'] += tk[0]; bucket['read'] += tk[1]; bucket['write'] += tk[2] + tk[3]; bucket['out'] += tk[4]
                    bucket['$'] += cost
                chats[t.id]['day'] = local
    if not day:
        print('no usage saved yet (it starts with the first coach message after this is deployed)')
        return
    print(f'{"day":12}{"msgs":>6}{"calls":>7}{"in":>9}{"read":>10}{"write":>9}{"out":>9}{"$":>9}{"$/msg":>8}')
    total = collections.Counter()
    for k in sorted(day):
        v = day[k]; total.update(v)
        print(f'{k:12}{v["requests"]:>6}{v["calls"]:>7}{v["in"]:>9}{v["read"]:>10}{v["write"]:>9}{v["out"]:>9}'
              f'{v["$"]:>9.2f}{v["$"] / v["requests"]:>8.3f}')
    print(f'{"total":12}{total["requests"]:>6}{total["calls"]:>7}{total["in"]:>9}{total["read"]:>10}{total["write"]:>9}'
          f'{total["out"]:>9}{total["$"]:>9.2f}{total["$"] / total["requests"]:>8.3f}')
    if total['$']:
        print('\nwhere the dollars go (at Sonnet 5.5 prices):',
              ', '.join(f'{k} {100 * total[k] * p / 1e6 / total["$"]:.0f}%'
                        for k, p in zip(('in', 'read', 'write', 'out'), (2.00, 0.20, 4.00, 10.00))))
    print(f'\ncostliest {a.chats} chats:')
    for cid, v in sorted(chats.items(), key=lambda kv: -kv[1]['$'])[:a.chats]:
        print(f'  {v["day"]} {cid[:12]}  {v["requests"]} msgs, {v["calls"]} calls, ${v["$"]:.3f}')
    if unpriced:
        print('\nno price for:', ', '.join(sorted(unpriced)), '(counted as $0; add it to PRICES)')


if __name__ == '__main__':
    main()
