"""
Read and write workouts in users/{uid}/assigned and users/{uid}/completed (#19).

Settings come from config/wilo.json, and the workout shape from
schema/workout.schema.json. Output is JSON on stdout.

    .venv/bin/python -m wilo.data completed [--limit N]
    .venv/bin/python -m wilo.data assigned [--limit N]
    .venv/bin/python -m wilo.data get <assigned|completed> <docId>
    .venv/bin/python -m wilo.data assign <file.json|-> [--write]
    .venv/bin/python -m wilo.data history <exercise name> [--limit N]
    .venv/bin/python -m wilo.data names
    .venv/bin/python -m wilo.data update <assigned|completed> <docId> <file.json|-> [--write]

assign and update are dry runs unless --write is passed. GOOGLE_APPLICATION_CREDENTIALS,
if set, overrides the key path in the config.
"""

import argparse
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
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER)
ORDER_FIELD = {'assigned': 'assignedFor', 'completed': 'finishedAt'}


def validate(doc):
    """Schema errors as readable strings, e.g. 'exercises/0/sets/1/reps: -5 is not valid ...'."""
    return [f"{'/'.join(map(str, e.absolute_path)) or '(workout)'}: {e.message}"
            for e in sorted(VALIDATOR.iter_errors(doc), key=lambda e: list(map(str, e.absolute_path)))]


def with_defaults(doc, now):
    """Fill the fields the coach shouldn't have to make up: id and assignedFor."""
    doc = dict(doc)
    doc.setdefault('id', f"prog_{int(now.timestamp() * 1000)}")
    doc.setdefault('assignedFor', now.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'))
    return doc


def doc_id(doc, now):
    """Tracker-style ID, e.g. 06-oct-07:11-legs-."""
    slug = re.sub(r'\s+', '-', doc.get('name', 'workout')[:5].lower())
    return f"{now.astimezone().strftime('%d-%b-%H:%M').lower()}-{slug}"


def connect():
    import firebase_admin
    from firebase_admin import credentials, firestore
    key = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') or os.path.expanduser(CONFIG['credentials'])
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(key), {'projectId': CONFIG['project']})
    return firestore.client(database_id=CONFIG['database'])


def collection(db, name):
    return db.collection('users').document(CONFIG['uid']).collection(name)


def recent(db, name, limit):
    from firebase_admin import firestore
    q = collection(db, name).order_by(ORDER_FIELD[name], direction=firestore.Query.DESCENDING).limit(limit)
    return [{'docId': d.id, **d.to_dict()} for d in q.stream()]


def _plain(word):
    return word[:-1] if len(word) > 3 and word.endswith('s') and not word.endswith('ss') else word


def name_matches(query, name):
    """Loose match for cosmetic differences only: case, spacing, punctuation, plurals, word order.
    Synonyms ("crane-plane" vs "Basic cranes") are left to the LLM, using `names`."""
    words = lambda s: {_plain(w) for w in re.findall(r'[a-z0-9]+', s.lower())}
    squash = lambda s: _plain(re.sub(r'[^a-z0-9]', '', s.lower()))
    return words(query) <= words(name) or squash(query) in squash(name)


def _completed(db):
    docs = [{'docId': d.id, **d.to_dict()} for d in collection(db, 'completed').stream()]
    return sorted(docs, key=lambda w: w.get('finishedAt', ''), reverse=True)


def history(db, query, limit):
    """Past sets for exercises whose name matches, newest first."""
    out = []
    for w in _completed(db):
        for e in w['exercises']:
            if name_matches(query, e['name']):
                out.append({'finishedAt': w.get('finishedAt'), 'workout': w['name'], 'docId': w['docId'],
                            'name': e['name'], 'custom_name': e.get('custom_name'), 'sets': e['sets']})
    return out[:limit]


def names(db):
    """Every distinct exercise name in completed workouts, with how often and when it was last done."""
    seen = {}
    for w in _completed(db):
        for e in w['exercises']:
            n = seen.setdefault(e['name'], {'name': e['name'], 'count': 0, 'lastDone': w.get('finishedAt')})
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


def update(db, name, doc_id, doc, write):
    """Replace an existing workout with an edited version. Never creates; keeps the same id."""
    doc = {k: v for k, v in doc.items() if k != 'docId'}  # `get` adds docId; it isn't part of the doc
    path = f"users/{CONFIG['uid']}/{name}/{doc_id}"
    ref = collection(db, name).document(doc_id)
    snap = ref.get()
    if not snap.exists:
        return {'ok': False, 'errors': [f'{path} not found (use assign to create)']}
    old = snap.to_dict()
    if doc.get('id') != old.get('id'):
        return {'ok': False, 'errors': [f"id changed: {old.get('id')!r} -> {doc.get('id')!r}"]}
    errors = validate(doc)
    if errors:
        return {'ok': False, 'errors': errors}
    changes = diff(old, doc)
    if not write or not changes:
        return {'ok': True, 'dryRun': not write, 'path': path, 'changes': changes}
    ref.set(doc)
    return {'ok': ref.get().to_dict() == doc, 'path': path, 'changes': changes}


def assign(db, doc, write, now):
    doc = with_defaults(doc, now)
    errors = validate(doc)
    path = f"users/{CONFIG['uid']}/assigned/{doc_id(doc, now)}"
    if errors:
        return {'ok': False, 'errors': errors}
    if not write:
        return {'ok': True, 'dryRun': True, 'path': path, 'doc': doc}
    ref = collection(db, 'assigned').document(path.rsplit('/', 1)[1])
    if ref.get().exists:
        return {'ok': False, 'errors': [f'{path} already exists']}
    ref.set(doc)
    return {'ok': ref.get().to_dict() == doc, 'path': path, 'doc': doc}


def main(argv=None):
    p = argparse.ArgumentParser(description='Read and write WILO workouts.')
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('completed', 'assigned'):
        sub.add_parser(name).add_argument('--limit', type=int, default=5)
    g = sub.add_parser('get')
    g.add_argument('collection', choices=['assigned', 'completed'])
    g.add_argument('doc_id')
    a = sub.add_parser('assign')
    a.add_argument('file', help='workout JSON file, or - for stdin')
    a.add_argument('--write', action='store_true', help='post it (default is a dry run)')
    h = sub.add_parser('history')
    h.add_argument('name', help='exercise name; loose match (case, spacing, punctuation, plurals, word order)')
    h.add_argument('--limit', type=int, default=5)
    sub.add_parser('names')
    u = sub.add_parser('update')
    u.add_argument('collection', choices=['assigned', 'completed'])
    u.add_argument('doc_id')
    u.add_argument('file', help='edited workout JSON file, or - for stdin')
    u.add_argument('--write', action='store_true', help='save it (default is a dry run)')
    args = p.parse_args(argv)

    db = connect()
    read = lambda f: json.loads(sys.stdin.read() if f == '-' else Path(f).read_text())
    if args.cmd in ('completed', 'assigned'):
        out = recent(db, args.cmd, args.limit)
    elif args.cmd == 'get':
        snap = collection(db, args.collection).document(args.doc_id).get()
        out = {'docId': snap.id, **snap.to_dict()} if snap.exists else {'ok': False, 'errors': ['not found']}
    elif args.cmd == 'history':
        out = history(db, args.name, args.limit)
    elif args.cmd == 'names':
        out = names(db)
    elif args.cmd == 'update':
        out = update(db, args.collection, args.doc_id, read(args.file), args.write)
    else:
        out = assign(db, read(args.file), args.write, datetime.now(timezone.utc))

    print(json.dumps(out, indent=2, default=str))
    return 1 if isinstance(out, dict) and out.get('ok') is False else 0


if __name__ == '__main__':
    sys.exit(main())
