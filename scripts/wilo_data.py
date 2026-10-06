#!/usr/bin/env python3
"""
Read and write workouts in users/{uid}/assigned and users/{uid}/completed (#19).

Settings come from config/wilo.json, and the workout shape from
schema/workout.schema.json. Output is JSON on stdout.

    .venv/bin/python scripts/wilo_data.py completed [--limit N]
    .venv/bin/python scripts/wilo_data.py assigned [--limit N]
    .venv/bin/python scripts/wilo_data.py get <assigned|completed> <docId>
    .venv/bin/python scripts/wilo_data.py assign <file.json|-> [--write]

assign is a dry run unless --write is passed. GOOGLE_APPLICATION_CREDENTIALS,
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
    args = p.parse_args(argv)

    db = connect()
    if args.cmd in ('completed', 'assigned'):
        out = recent(db, args.cmd, args.limit)
    elif args.cmd == 'get':
        snap = collection(db, args.collection).document(args.doc_id).get()
        out = {'docId': snap.id, **snap.to_dict()} if snap.exists else {'ok': False, 'errors': ['not found']}
    else:
        raw = sys.stdin.read() if args.file == '-' else Path(args.file).read_text()
        out = assign(db, json.loads(raw), args.write, datetime.now(timezone.utc))

    print(json.dumps(out, indent=2, default=str))
    return 1 if isinstance(out, dict) and out.get('ok') is False else 0


if __name__ == '__main__':
    sys.exit(main())
