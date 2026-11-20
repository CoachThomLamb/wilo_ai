"""Import a Hevy CSV export into a user's completed workouts (#111).

    .venv/bin/python -m wilo.hevy_import workouts.csv --uid <uid>           # dry run: parse, validate, summarize
    .venv/bin/python -m wilo.hevy_import workouts.csv --uid <uid> --write   # write to users/<uid>/completed

The dry run doesn't touch Firestore. --write uses the admin key (wilo.data.connect) and skips workouts that are
already there: doc IDs come from the Hevy start time, so re-running never makes duplicates.
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from wilo import data as wilo_data

LBS_PER_KG = 2.20462
TIME_FORMATS = ('%d %b %Y, %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M')


def parse_time(text, tz):
    """Hevy times are local, e.g. '24 Sep 2026, 18:02'. Returns an aware datetime in tz."""
    text = text.strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=tz)
        except ValueError:
            pass
    return datetime.fromisoformat(text).astimezone(tz)


def number(text):
    text = (text or '').strip()
    if not text:
        return None
    n = float(text)
    return int(n) if n.is_integer() else n


def iso_z(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def to_set(row):
    """One Hevy row → one WILO set, plus whether it's timed. Everything without a WILO field goes in custom."""
    kg, lbs = number(row.get('weight_kg')), number(row.get('weight_lbs'))
    if lbs is None and kg is not None:
        lbs = round(kg * LBS_PER_KG * 2) / 2  # nearest half pound
    reps, seconds = number(row.get('reps')), number(row.get('duration_seconds'))
    timed = reps is None and seconds is not None
    extra = []
    if (row.get('set_type') or 'normal').strip() not in ('', 'normal'):
        extra.append(row['set_type'].strip())
    for col, unit in (('distance_km', 'km'), ('distance_miles', 'mi')):
        if number(row.get(col)) is not None:
            extra.append(f'{number(row[col])} {unit}')
    if number(row.get('rpe')) is not None:
        extra.append(f"RPE {number(row['rpe'])}")
    return {'lbs': '' if lbs is None else lbs, 'reps': seconds if timed else ('' if reps is None else reps),
            'done': True, 'custom': ', '.join(extra) or None}, timed


def workouts(rows, tz):
    """Hevy rows (one per set) → WILO completed workouts, oldest first, keyed by doc ID."""
    out = {}
    for row in rows:
        start = parse_time(row['start_time'], tz)
        doc_id = f"hevy-{start:%Y%m%d-%H%M}"
        w = out.get(doc_id)
        if w is None:
            end = parse_time(row['end_time'], tz) if (row.get('end_time') or '').strip() else start
            w = out[doc_id] = {'id': doc_id, 'name': row['title'].strip(), 'source': 'hevy',
                               'startedAt': iso_z(start), 'finishedAt': iso_z(end), 'inProgress': False,
                               'exercises': []}
            if (row.get('description') or '').strip():
                w['note'] = row['description'].strip()
        name = row['exercise_title'].strip()
        ex = w['exercises'][-1] if w['exercises'] else None
        if ex is None or ex['name'] != name:  # a new exercise starts; a repeat later in the workout is its own entry
            ex = {'name': name, 'timed': False, 'cue': '', 'note': (row.get('exercise_notes') or '').strip(),
                  'custom_name': None, 'sets': []}
            w['exercises'].append(ex)
        s, timed = to_set(row)
        ex['sets'].append(s)
        ex['timed'] = ex['timed'] or timed
        if s['custom']:
            ex['custom_name'] = 'Hevy'
    return dict(sorted(out.items(), key=lambda kv: kv[1]['startedAt']))


def load(path, tz):
    with open(path, newline='', encoding='utf-8-sig') as f:
        docs = workouts(csv.DictReader(f), tz)
    errors = {doc_id: e for doc_id, doc in docs.items() if (e := wilo_data.validate(doc))}
    return docs, errors


def write(db, uid, docs):
    """Write the docs that aren't there yet. Returns (written, skipped) doc IDs."""
    written, skipped = [], []
    col = wilo_data.collection(db, uid, 'completed')
    for doc_id, doc in docs.items():
        ref = col.document(doc_id)
        if ref.get().exists:
            skipped.append(doc_id)
        else:
            ref.set(doc)
            written.append(doc_id)
    return written, skipped


def main(argv=None):
    p = argparse.ArgumentParser(description='Import a Hevy CSV export into users/<uid>/completed.')
    p.add_argument('csv')
    p.add_argument('--uid', required=True, help="the user's Firebase uid (Firebase console → Authentication)")
    p.add_argument('--tz', default='America/Toronto', help='the time zone the Hevy times are in')
    p.add_argument('--write', action='store_true', help='write to Firestore (default: dry run, no Firestore)')
    args = p.parse_args(argv)

    docs, errors = load(args.csv, ZoneInfo(args.tz))
    if errors:
        print(json.dumps(errors, indent=2))
        sys.exit(f'{len(errors)} workouts fail the schema; nothing written.')
    if not docs:
        sys.exit('No workouts in the file.')
    first, last = next(iter(docs.values())), list(docs.values())[-1]
    sets = sum(len(e['sets']) for d in docs.values() for e in d['exercises'])
    print(f"{len(docs)} workouts, {sets} sets, {first['startedAt'][:10]} to {last['startedAt'][:10]}, for {args.uid}")
    print('Sample:', json.dumps(last, indent=2))
    if not args.write:
        print('Dry run: nothing written. Add --write to import.')
        return
    written, skipped = write(wilo_data.connect(), args.uid, docs)
    print(f'Wrote {len(written)}, skipped {len(skipped)} already there.')


if __name__ == '__main__':
    main()
