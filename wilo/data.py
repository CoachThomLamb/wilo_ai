"""
Read and write workouts in users/{uid}/workouts (#126), todos in users/{uid}/todos (#64) and the
coaching profile in users/{uid}/coach/profile (#48; no CLI commands for those two yet).

A workout is one doc from plan to done: the plan as first written, the coach's diffs to it, the
plan as it is now (`exercises` = apply_diffs(plan, diffs), written here with each diff), and the
user's log, which only the tracker writes. The coach never touches the log; the tracker never
touches the plan.

Settings come from config/wilo.json, and the workout shape from
schema/workout.schema.json. Output is JSON on stdout.

    .venv/bin/python -m wilo.data recent [--status planned|"in progress"|done] [--limit N]
    .venv/bin/python -m wilo.data get <docId>
    .venv/bin/python -m wilo.data assign <file.json|-> [--write]
    .venv/bin/python -m wilo.data change <docId> <ops.json|-> [--write]
    .venv/bin/python -m wilo.data history <exercise name> [--limit N]
    .venv/bin/python -m wilo.data names

assign and change are dry runs unless --write is passed. GOOGLE_APPLICATION_CREDENTIALS,
if set, overrides the key path in the config.
"""

import argparse
import copy
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / 'config' / 'wilo.json').read_text())
SCHEMA = json.loads((ROOT / 'schema' / 'workout.schema.json').read_text())
WORKOUTS = 'workouts'
STATUSES = ('planned', 'in progress', 'done')


def _validator(name):
    return Draft202012Validator({**SCHEMA, '$ref': f'#/$defs/{name}'}, format_checker=Draft202012Validator.FORMAT_CHECKER)


VALIDATORS = {name: _validator(name) for name in ('workout', 'plannedWorkout', 'op')}


def validate(doc, kind='workout'):
    """Schema errors as readable strings, e.g. 'exercises/0/sets/1/reps: -5 is not valid ...'.
    kind: 'workout' (a stored doc), 'plannedWorkout' (what assign takes) or 'op' (one diff op)."""
    return [f"{'/'.join(map(str, e.absolute_path)) or '(workout)'}: {e.message}"
            for e in sorted(VALIDATORS[kind].iter_errors(doc), key=lambda e: list(map(str, e.absolute_path)))]


def _iso(now):
    return now.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def doc_id(doc, now):
    """Tracker-style ID, e.g. 06-oct-07:11-legs-."""
    slug = re.sub(r'\s+', '-', doc.get('name', 'workout')[:5].lower())
    return f"{now.astimezone().strftime('%d-%b-%H:%M').lower()}-{slug}"


def connect():
    import firebase_admin
    from firebase_admin import credentials, firestore
    key = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') or os.path.expanduser(CONFIG['credentials'])
    # No key file (e.g. on Cloud Run): use the environment's own identity, so no JSON key ships in the container.
    cred = credentials.Certificate(key) if os.path.exists(key) else credentials.ApplicationDefault()
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {'projectId': CONFIG['project']})
    return firestore.client(database_id=CONFIG['database'])


def collection(db, uid, name):
    return db.collection('users').document(uid).collection(name)


# ---- the plan: diffs -------------------------------------------------------

def _find(exercises, ex_id):
    for i, x in enumerate(exercises):
        if x.get('exId') == ex_id:
            return i
    raise ValueError(f'no exercise with exId {ex_id!r}')


def apply_diffs(plan, diffs):
    """The plan as it is now: every diff's ops applied in order, to a copy. The one place diffs mean anything.
    Returns (exercises, workout_fields) where workout_fields holds a 'workout' op's name/assignedFor.
    Raises ValueError on an op that doesn't fit (unknown exId, ...)."""
    exercises, fields = copy.deepcopy(plan), {}
    for d in diffs:
        for op in d['ops']:
            kind = op['op']
            if kind == 'add':
                exercises.insert(op.get('at', len(exercises)), copy.deepcopy(op['exercise']))
            elif kind == 'remove':
                exercises.pop(_find(exercises, op['exId']))
            elif kind == 'replace':
                exercises[_find(exercises, op['exId'])] = copy.deepcopy(op['exercise'])
            elif kind == 'move':
                exercises.insert(op['to'], exercises.pop(_find(exercises, op['exId'])))
            elif kind == 'set':
                exercises[_find(exercises, op['exId'])].update(copy.deepcopy(op['fields']))
            elif kind == 'workout':
                fields.update({k: op[k] for k in ('name', 'assignedFor') if k in op})
    return exercises, fields


def _with_ids(exercises, next_id):
    """Give each exercise a new server exId (x1, x2, ...). Returns (exercises, next_id)."""
    out = []
    for x in exercises:
        out.append({**x, 'exId': f'x{next_id}'})
        next_id += 1
    return out, next_id


def _planned_sets(exercises):
    """The plan's sets are what to do, never what was done."""
    return [{**x, 'sets': [{**s, 'done': False} for s in x.get('sets', [])]} for x in exercises]


def assign(db, uid, workout, write, now):
    """Plan a new workout: status planned, every exercise gets an exId. Dry run unless write."""
    errors = validate(workout, 'plannedWorkout')
    if errors:
        return {'ok': False, 'errors': errors}
    plan, next_id = _with_ids(_planned_sets(workout['exercises']), 1)
    doc = {'id': f'prog_{int(now.timestamp() * 1000)}', 'name': workout['name'],
           'assignedFor': workout.get('assignedFor') or _iso(now), 'status': 'planned', 'createdAt': _iso(now),
           'plan': plan, 'diffs': [], 'exercises': plan, 'nextExId': next_id, 'log': [], 'logBase': 0}
    path = f'users/{uid}/{WORKOUTS}/{doc_id(doc, now)}'
    errors = validate(doc)
    if errors:
        return {'ok': False, 'errors': errors}
    if not write:
        return {'ok': True, 'dryRun': True, 'path': path, 'doc': doc}
    ref = collection(db, uid, WORKOUTS).document(path.rsplit('/', 1)[1])
    if ref.get().exists:
        return {'ok': False, 'errors': [f'{path} already exists']}
    ref.set(doc)
    return {'ok': ref.get().to_dict() == doc, 'path': path, 'doc': doc}


def change(db, uid, doc_id, ops, write, now):
    """Add one diff (a list of ops) to a workout's plan. Returns the plan as it would be / now is.
    Refuses a done workout: its plan is history. Never touches the log. Dry run unless write."""
    path = f'users/{uid}/{WORKOUTS}/{doc_id}'
    ref = collection(db, uid, WORKOUTS).document(doc_id)
    snap = ref.get()
    if not snap.exists:
        return {'ok': False, 'errors': [f'{path} not found']}
    doc = snap.to_dict()
    if doc.get('status') == 'done':
        return {'ok': False, 'errors': [f'{path} is done; its plan is history']}
    if not ops:
        return {'ok': False, 'errors': ['no ops']}
    errors = [f'ops/{i}/{e}' for i, op in enumerate(ops) for e in validate(op, 'op')]
    if errors:
        return {'ok': False, 'errors': errors}
    next_id, stored = doc.get('nextExId', 1), []
    for op in ops:  # new exercises get their exId now, so replaying the diffs always gives the same ids
        op = copy.deepcopy(op)
        if op['op'] in ('add', 'replace'):
            (op['exercise'],), next_id = _with_ids(_planned_sets([op['exercise']]), next_id)
        if op['op'] == 'set' and 'sets' in op['fields']:
            op['fields']['sets'] = _planned_sets([{'sets': op['fields']['sets']}])[0]['sets']
        stored.append(op)
    diffs = doc.get('diffs', []) + [{'at': _iso(now), 'ops': stored}]
    try:
        exercises, fields = apply_diffs(doc.get('plan', []), diffs)
    except ValueError as e:
        return {'ok': False, 'errors': [str(e)]}
    update = {'diffs': diffs, 'exercises': exercises, 'nextExId': next_id, **fields}
    errors = validate({**doc, **update})
    if errors:
        return {'ok': False, 'errors': errors}
    if not write:
        return {'ok': True, 'dryRun': True, 'path': path, 'exercises': exercises, **fields}
    ref.update(update)  # only the plan's fields: the tracker's log is left as it is
    return {'ok': True, 'path': path, 'exercises': exercises, **fields}


# ---- reading ---------------------------------------------------------------

def when(w):
    """What to sort a workout by: when it was finished, else last logged, else the date it's for."""
    return w.get('finishedAt') or w.get('updatedAt') or w.get('assignedFor') or ''


def workouts(db, uid, status=None):
    """The user's workouts, newest first; only one status if given."""
    docs = [{'docId': d.id, **d.to_dict()} for d in collection(db, uid, WORKOUTS).stream()]
    return sorted([w for w in docs if not status or w.get('status') == status], key=when, reverse=True)


def recent(db, uid, status, limit):
    return workouts(db, uid, status)[:limit]


def get(db, uid, doc_id):
    snap = collection(db, uid, WORKOUTS).document(doc_id).get()
    return {'docId': snap.id, **snap.to_dict()} if snap.exists else {'ok': False, 'errors': ['not found']}


def _logged(db, uid):
    """Workouts with something logged (in progress or done), newest first, with the exercises the user kept."""
    out = []
    for w in workouts(db, uid):
        kept = [x for x in w.get('log', []) if not x.get('removed')]
        if kept:
            out.append({**w, 'log': kept})
    return out


def _plain(word):
    return word[:-1] if len(word) > 3 and word.endswith('s') and not word.endswith('ss') else word


def name_matches(query, name):
    """Loose match for cosmetic differences only: case, spacing, punctuation, plurals, word order.
    Synonyms ("crane-plane" vs "Basic cranes") are left to the LLM, using `names`."""
    words = lambda s: {_plain(w) for w in re.findall(r'[a-z0-9]+', s.lower())}
    squash = lambda s: _plain(re.sub(r'[^a-z0-9]', '', s.lower()))
    return words(query) <= words(name) or squash(query) in squash(name)


def history(db, uid, query, limit):
    """Logged sets for exercises whose name matches, newest first."""
    out = []
    for w in _logged(db, uid):
        for e in w['log']:
            if name_matches(query, e['name']):
                out.append({'finishedAt': w.get('finishedAt'), 'status': w.get('status'), 'workout': w['name'],
                            'docId': w['docId'], 'name': e['name'], 'custom_name': e.get('custom_name'), 'sets': e['sets']})
    return out[:limit]


def names(db, uid):
    """Every distinct exercise name the user has logged, with how often and when it was last done."""
    seen = {}
    for w in _logged(db, uid):
        for e in w['log']:
            n = seen.setdefault(e['name'], {'name': e['name'], 'count': 0, 'lastDone': when(w)})
            n['count'] += 1
    return sorted(seen.values(), key=lambda n: n['name'].strip().lower())


def diff(old, new, path=''):
    """Changes between two docs as 'path: old -> new' strings."""
    if isinstance(old, dict) and isinstance(new, dict):
        return [c for k in sorted(set(old) | set(new), key=str)
                for c in diff(old.get(k, '<missing>'), new.get(k, '<missing>'), f'{path}/{k}' if path else str(k))]
    if isinstance(old, list) and isinstance(new, list):
        n = max(len(old), len(new))
        pad = lambda xs: xs + ['<missing>'] * (n - len(xs))
        return [c for i, (a, b) in enumerate(zip(pad(old), pad(new))) for c in diff(a, b, f'{path}/{i}')]
    return [] if old == new else [f'{path}: {json.dumps(old, default=str)} -> {json.dumps(new, default=str)}']


TODO_FIELDS = ('text', 'done', 'due', 'notes')  # loose on purpose: free text, due like '2026-10-12' or '2026-10-12 19:00'


def todos(db, uid, include_done=False):
    """Todos, open first: dated ones by due (earliest first), then undated by when they were added."""
    docs = [{'docId': d.id, **d.to_dict()} for d in collection(db, uid, 'todos').stream()]
    docs = [t for t in docs if include_done or not t.get('done')]
    return sorted(docs, key=lambda t: (bool(t.get('done')), not t.get('due'), t.get('due') or '', t.get('createdAt', '')))


def add_todo(db, uid, text, now, due=None, notes=None):
    """Add a todo. Saves immediately: todos skip the dry run that workouts have."""
    if not str(text).strip():
        return {'ok': False, 'errors': ['text is empty']}
    todo = {'text': str(text).strip(), 'done': False, 'createdAt': _iso(now)}
    todo.update({k: v for k, v in (('due', due), ('notes', notes)) if v})
    ref = collection(db, uid, 'todos').document(f"todo_{int(now.timestamp() * 1000)}")
    if ref.get().exists:
        return {'ok': False, 'errors': [f'users/{uid}/todos/{ref.get().id} already exists']}
    ref.set(todo)
    return {'ok': True, 'docId': ref.get().id, 'todo': todo}


def update_todo(db, uid, doc_id, changes, now):
    """Change a todo's text, done, due or notes. None leaves a field as is; '' clears due or notes."""
    ref = collection(db, uid, 'todos').document(doc_id)
    snap = ref.get()
    if not snap.exists:
        return {'ok': False, 'errors': [f'users/{uid}/todos/{doc_id} not found']}
    old = snap.to_dict()
    new = dict(old)
    for k, v in changes.items():
        if k not in TODO_FIELDS:
            return {'ok': False, 'errors': [f'unknown field {k!r} (allowed: {", ".join(TODO_FIELDS)})']}
        if v is None:
            continue
        if v == '' and k in ('due', 'notes'):
            new.pop(k, None)
        else:
            new[k] = v
    if not str(new.get('text', '')).strip():
        return {'ok': False, 'errors': ['text is empty']}
    if new.get('done') and not old.get('done'):
        new['doneAt'] = _iso(now)
    elif not new.get('done'):
        new.pop('doneAt', None)
    ref.set(new)
    return {'ok': True, 'docId': doc_id, 'todo': new, 'changes': diff(old, new)}


def delete_todo(db, uid, doc_id):
    ref = collection(db, uid, 'todos').document(doc_id)
    snap = ref.get()
    if not snap.exists:
        return {'ok': False, 'errors': [f'users/{uid}/todos/{doc_id} not found']}
    ref.delete()
    return {'ok': True, 'deleted': {'docId': doc_id, **snap.to_dict()}}


# The coaching profile (#48): what's personal to this user, as opposed to the generic method in wilo/coach.md.
# Loose on purpose: free-text sections, formalized only once real use shows what's needed.
PROFILE_SECTIONS = ('preferences', 'limitations', 'plan', 'notes')


def _profile_ref(db, uid):
    return collection(db, uid, 'coach').document('profile')


def profile(db, uid):
    """The user's coaching profile. A new user has none yet: empty sections, exists=False."""
    snap = _profile_ref(db, uid).get()
    doc = snap.to_dict() if snap.exists else {}
    return {'exists': snap.exists, 'profile': {k: doc.get(k, '') for k in PROFILE_SECTIONS},
            'updatedAt': doc.get('updatedAt')}


def update_profile(db, uid, new, write, now):
    """Edit the profile: each section passed replaces that section (free text, '' empties it); sections left out
    stay as they are. Returns the changes; a dry run unless write is True."""
    unknown = sorted(set(new) - set(PROFILE_SECTIONS))
    if unknown:
        return {'ok': False, 'errors': [f'unknown section {k!r} (allowed: {", ".join(PROFILE_SECTIONS)})' for k in unknown]}
    bad = [k for k, v in new.items() if not isinstance(v, str)]
    if bad:
        return {'ok': False, 'errors': [f'{k} must be text' for k in bad]}
    path = f'users/{uid}/coach/profile'
    old = profile(db, uid)['profile']
    doc = {k: new[k].strip() if k in new else old[k] for k in PROFILE_SECTIONS}
    changes = diff(old, doc)
    if not write or not changes:
        return {'ok': True, 'dryRun': not write, 'path': path, 'changes': changes}
    ref = _profile_ref(db, uid)
    ref.set({**{k: v for k, v in doc.items() if v}, 'updatedAt': _iso(now)})
    return {'ok': True, 'path': path, 'changes': changes}


def main(argv=None):
    p = argparse.ArgumentParser(description='Read and write WILO workouts.')
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('recent')
    r.add_argument('--status', choices=STATUSES)
    r.add_argument('--limit', type=int, default=5)
    sub.add_parser('get').add_argument('doc_id')
    a = sub.add_parser('assign')
    a.add_argument('file', help='workout JSON file, or - for stdin')
    a.add_argument('--write', action='store_true', help='post it (default is a dry run)')
    c = sub.add_parser('change')
    c.add_argument('doc_id')
    c.add_argument('file', help='JSON list of ops, or - for stdin')
    c.add_argument('--write', action='store_true', help='save it (default is a dry run)')
    h = sub.add_parser('history')
    h.add_argument('name', help='exercise name; loose match (case, spacing, punctuation, plurals, word order)')
    h.add_argument('--limit', type=int, default=5)
    sub.add_parser('names')
    args = p.parse_args(argv)

    db, uid, now = connect(), CONFIG['uid'], datetime.now(timezone.utc)  # the command line acts as the user in config
    read = lambda f: json.loads(sys.stdin.read() if f == '-' else Path(f).read_text())
    if args.cmd == 'recent':
        out = recent(db, uid, args.status, args.limit)
    elif args.cmd == 'get':
        out = get(db, uid, args.doc_id)
    elif args.cmd == 'history':
        out = history(db, uid, args.name, args.limit)
    elif args.cmd == 'names':
        out = names(db, uid)
    elif args.cmd == 'change':
        out = change(db, uid, args.doc_id, read(args.file), args.write, now)
    else:
        out = assign(db, uid, read(args.file), args.write, now)

    print(json.dumps(out, indent=2, default=str))
    return 1 if isinstance(out, dict) and out.get('ok') is False else 0


if __name__ == '__main__':
    sys.exit(main())
