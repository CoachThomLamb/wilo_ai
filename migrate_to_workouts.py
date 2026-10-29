#!/usr/bin/env python3
"""
Move every user's assigned + completed workouts into one users/{uid}/workouts collection (#126).

    .venv/bin/python migrate_to_workouts.py            # dry run: what it would write, per user
    .venv/bin/python migrate_to_workouts.py --write    # backs up first, then writes

- An assigned workout and its completed copy (same `id` field) become one doc, under the assigned
  doc's id: plan = the assigned exercises, log = the completed copy's, status from inProgress.
- An assigned workout with no copy: status planned, empty log.
- A completed workout with no plan (logged by hand, or a second copy): its own done doc, empty plan.
- Exercises get exIds: x1, x2, ... in the plan; a logged exercise takes the plan's id when the name
  matches, else u-m1, u-m2, ...
- Never deletes or changes assigned/completed: they stay as they are until a later cleanup.
  A workouts doc that already exists is skipped, so it's safe to run again.
- --write first dumps assigned, completed and workouts of every user to
  data/backup-<date>-pre-workouts/users__<uid>__<collection>.json (the format of the older backups).
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from wilo import data as wilo_data

ROOT = Path(__file__).resolve().parent


def norm(name):
    return re.sub(r'[^a-z0-9]', '', (name or '').lower())


def planned(exercises):
    """Plan exercises with server ids and no done sets."""
    return [{**{k: v for k, v in x.items() if k not in ('instanceId', 'exId')}, 'exId': f'x{i}',
             'sets': [{**s, 'done': False} for s in x.get('sets', [])]} for i, x in enumerate(exercises, 1)]


def logged(exercises, plan):
    """A completed copy's exercises as a log: each takes the plan's exId when the name matches."""
    free = {}
    for x in plan:
        free.setdefault(norm(x['name']), []).append(x['exId'])
    out, n = [], 0
    for x in exercises:
        ids = free.get(norm(x.get('name')))
        if ids:
            ex_id = ids.pop(0)
        else:
            n += 1
            ex_id = f'u-m{n}'
        out.append({**{k: v for k, v in x.items() if k not in ('instanceId', 'exId')}, 'exId': ex_id})
    return out


def finished(c):
    return str(c.get('finishedAt') or '')


def merge(assigned, completed):
    """{docId: new workouts doc} for one user."""
    copies = {}
    for doc_id, c in completed.items():
        copies.setdefault(c.get('id'), []).append((doc_id, c))
    out = {}
    for doc_id, a in assigned.items():
        plan = planned(a.get('exercises', []))
        doc = {'id': a.get('id') or doc_id, 'name': a.get('name', 'Workout'), 'assignedFor': a.get('assignedFor'),
               'status': 'planned', 'plan': plan, 'diffs': [], 'exercises': plan, 'nextExId': len(plan) + 1,
               'log': [], 'logBase': 0}
        mine = sorted(copies.pop(a.get('id'), []), key=lambda dc: (not dc[1].get('inProgress'), finished(dc[1])))
        if mine:
            _, c = mine.pop()  # the finished one if any, else the newest in progress
            doc.update(log=logged(c.get('exercises', []), plan), updatedAt=c.get('finishedAt'),
                       status='in progress' if c.get('inProgress') else 'done')
            if doc['status'] == 'done':
                doc['finishedAt'] = c.get('finishedAt')
        if not doc['assignedFor']:
            doc.pop('assignedFor')
        out[doc_id] = doc
        copies.setdefault('_extra', []).extend(mine)  # a workout logged twice: the others stand alone
    for doc_id, c in [dc for group in copies.values() for dc in group]:
        log = logged(c.get('exercises', []), [])
        doc = {'id': c.get('id') or doc_id, 'name': c.get('name', 'Workout'), 'status': 'in progress' if c.get('inProgress') else 'done',
               'assignedFor': c.get('finishedAt'), 'updatedAt': c.get('finishedAt'),
               'plan': [], 'diffs': [], 'exercises': [], 'nextExId': 1, 'log': log, 'logBase': 0}
        if doc['status'] == 'done':
            doc['finishedAt'] = c.get('finishedAt')
        out[doc_id if doc_id not in out else f'{doc_id}-log'] = {k: v for k, v in doc.items() if v is not None}
    return out


def read(db, uid, name):
    return {d.id: d.to_dict() for d in wilo_data.collection(db, uid, name).stream()}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    p.add_argument('--write', action='store_true', help='back up, then write (default is a dry run)')
    a = p.parse_args(argv)

    db = wilo_data.connect()
    uids = [ref.id for ref in db.collection('users').list_documents()]
    backup = ROOT / 'data' / f"backup-{datetime.now(timezone.utc):%Y-%m-%d}-pre-workouts"
    failed = False
    for uid in uids:
        cols = {name: read(db, uid, name) for name in ('assigned', 'completed', 'workouts')}
        new = merge(cols['assigned'], cols['completed'])
        bad = {doc_id: errs for doc_id, doc in new.items() if (errs := wilo_data.validate(doc))}
        skip = [doc_id for doc_id in new if doc_id in cols['workouts']]
        status = {s: sum(d['status'] == s for d in new.values()) for s in wilo_data.STATUSES}
        print(f"{uid}: {len(cols['assigned'])} assigned + {len(cols['completed'])} completed -> {len(new)} workouts "
              f"{status}, {len(skip)} already there, {len(bad)} invalid")
        for doc_id, errs in bad.items():
            print(f'  invalid {doc_id}: {errs[:3]}')
        failed |= bool(bad)
        if not a.write or bad:
            continue
        backup.mkdir(parents=True, exist_ok=True)
        for name, docs in cols.items():
            (backup / f'users__{uid}__{name}.json').write_text(json.dumps(docs, indent=2, default=str, ensure_ascii=False))
        for doc_id, doc in new.items():
            if doc_id not in skip:
                wilo_data.collection(db, uid, 'workouts').document(doc_id).set(doc)
        print(f'  wrote {len(new) - len(skip)}; backup in {backup}')
    if not a.write:
        print('dry run: nothing written (pass --write)')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
