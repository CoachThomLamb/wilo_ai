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
from firebase_admin import auth as firebase_auth  # noqa: E402
from wilo.token_cost import dollars, tokens  # noqa: E402

TZ = ZoneInfo('America/Toronto')
KINDS = ('in', 'read', 'write', 'out')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since', help='YYYY-MM-DD, local day')
    ap.add_argument('--chats', type=int, default=10, help='how many of the costliest chats to list')
    a = ap.parse_args()
    db = data.connect()
    day = collections.defaultdict(lambda: collections.Counter())
    chats = collections.defaultdict(lambda: collections.Counter())
    users = collections.defaultdict(lambda: collections.Counter())
    unpriced = set()
    for t in db.collection('chat_threads').stream():
        for u in t.reference.collection('usage').stream():
            d = u.to_dict()
            local = datetime.fromisoformat(d['at']).astimezone(TZ).date().isoformat()
            if a.since and local < a.since:
                continue
            uid = d.get('uid', '?')
            for key, bucket in ((local, day), (t.id, chats), (uid, users)):
                bucket[key]['requests'] += 1
            users[uid]['days'] = max(users[uid]['days'] or '', local)  # last active day
            users[uid]['first'] = min(users[uid]['first'] or '9999', local)
            for c in d.get('calls', []):
                tk = tokens(c.get('usage', {}))
                cost = dollars(c.get('model', ''), tk)
                if cost is None:
                    unpriced.add(c.get('model'))
                    cost = 0
                for bucket in (day[local], chats[t.id], users[uid]):
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
    print('\nper user (email from Firebase Auth, printed here only):')
    for uid, v in sorted(users.items(), key=lambda kv: -kv[1]['$']):
        try:
            who = firebase_auth.get_user(uid).email or uid
        except Exception:  # deleted user or no uid on old records
            who = uid
        print(f'  {who:32} {v["first"]} to {v["days"]}  {v["requests"]:>4} msgs  ${v["$"]:>7.2f}  '
              f'${v["$"] / v["requests"]:.3f}/msg')
    ratings = [f.to_dict() for f in db.collection('chat_feedback').stream()]
    ratings = [r for r in ratings if not a.since or r.get('at', '')[:10] >= a.since]
    print(f'\n"How\'s Wilo doing?": {len(ratings)} rated chats,',
          ', '.join(f'{k} {sum(r.get("rating") == k for r in ratings)}' for k in ('good', 'meh', 'bad')))
    for r in sorted(ratings, key=lambda r: r.get('at', '')):
        if r.get('note'):
            print(f'  {r["at"][:10]} {r["rating"]:5} {r["chatId"][:12]}  {r["note"]}')
    print(f'\ncostliest {a.chats} chats:')
    for cid, v in sorted(chats.items(), key=lambda kv: -kv[1]['$'])[:a.chats]:
        print(f'  {v["day"]} {cid[:12]}  {v["requests"]} msgs, {v["calls"]} calls, ${v["$"]:.3f}')
    if unpriced:
        print('\nno price for:', ', '.join(sorted(unpriced)), '(counted as $0; add it to PRICES)')


if __name__ == '__main__':
    main()
