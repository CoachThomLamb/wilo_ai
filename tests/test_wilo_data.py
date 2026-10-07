"""Tests for scripts/wilo_data.py. No Firestore access: assign() gets a fake db.

    .venv/bin/python -m unittest discover tests
"""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import wilo_data  # noqa: E402

NOW = datetime(2026, 10, 6, 11, 11, 56, 820000, tzinfo=timezone.utc)

MINIMAL = {'id': 'w1', 'name': 'legs', 'exercises': [
    {'name': 'squats', 'sets': [{'reps': 8, 'done': False}]}]}

# Shape the tracker writes today, extra fields included.
TRACKER = {'id': 'prog_1', 'name': 'legs-oct-6', 'finishedAt': '2026-10-06T13:16:29.498Z', 'exercises': [
    {'instanceId': 'ex1', 'exId': 'step-up', 'name': 'step up', 'timed': False, 'cue': '', 'note': 'felt good',
     'custom_name': 'Risers', 'fallback': None, 'swapped': False,
     'sets': [{'lbs': '', 'reps': 8, 'done': True, 'custom': '3'}, {'lbs': 30, 'reps': 6, 'done': False, 'custom': '4'}]}]}


class FakeRef:
    def __init__(self, store, key):
        self.store, self.key = store, key

    def get(self):
        data = self.store.get(self.key)
        return type('Snap', (), {'exists': data is not None, 'to_dict': lambda _: data})()

    def set(self, doc):
        self.store[self.key] = doc


class FakeDB:
    """Just enough of firestore.Client for assign()."""

    def __init__(self):
        self.store = {}

    def collection(self, name):
        db, path = self, [name]

        class Node:
            def document(self, d):
                path.append(d)
                return self

            def collection(self, c):
                path.append(c)
                return self

            def __getattr__(self, attr):
                ref = FakeRef(db.store, '/'.join(path))
                return getattr(ref, attr)

        return Node()


class SchemaTest(unittest.TestCase):
    def test_accepts_minimal_and_tracker_shapes(self):
        self.assertEqual(wilo_data.validate(MINIMAL), [])
        self.assertEqual(wilo_data.validate(TRACKER), [])

    def test_accepts_blank_lbs_and_reps(self):
        doc = {**MINIMAL, 'exercises': [{'name': 'x', 'sets': [{'lbs': '', 'reps': '', 'done': False}]}]}
        self.assertEqual(wilo_data.validate(doc), [])

    def test_rejects_broken_workouts(self):
        broken = {
            'missing exercise name': {**MINIMAL, 'exercises': [{'sets': []}]},
            'set without reps': {**MINIMAL, 'exercises': [{'name': 'x', 'sets': [{'done': False}]}]},
            'text weight': {**MINIMAL, 'exercises': [{'name': 'x', 'sets': [{'lbs': 'heavy', 'reps': 8, 'done': False}]}]},
            'negative reps': {**MINIMAL, 'exercises': [{'name': 'x', 'sets': [{'reps': -5, 'done': False}]}]},
            'done not boolean': {**MINIMAL, 'exercises': [{'name': 'x', 'sets': [{'reps': 8, 'done': 'yes'}]}]},
            'old nested shape': {'id': 'p', 'name': 'old', 'sessions': [{'blocks': []}]},
        }
        for label, doc in broken.items():
            with self.subTest(label):
                self.assertNotEqual(wilo_data.validate(doc), [])


class AssignTest(unittest.TestCase):
    def test_fills_id_and_assigned_for_without_overriding(self):
        filled = wilo_data.with_defaults({'name': 'legs', 'exercises': []}, NOW)
        self.assertEqual(filled['id'], 'prog_1791285116820')
        self.assertEqual(filled['assignedFor'], '2026-10-06T11:11:56.820Z')
        kept = wilo_data.with_defaults({'id': 'mine', 'assignedFor': '2026-10-08', 'name': 'x', 'exercises': []}, NOW)
        self.assertEqual((kept['id'], kept['assignedFor']), ('mine', '2026-10-08'))

    def test_doc_id_is_tracker_style(self):
        self.assertRegex(wilo_data.doc_id({'name': 'Pull Press'}, NOW), r'^\d{2}-[a-z]{3}-\d{2}:\d{2}-pull-$')

    def test_dry_run_writes_nothing(self):
        db = FakeDB()
        out = wilo_data.assign(db, MINIMAL, write=False, now=NOW)
        self.assertTrue(out['ok'] and out['dryRun'])
        self.assertEqual(db.store, {})

    def test_invalid_workout_is_not_written(self):
        db = FakeDB()
        out = wilo_data.assign(db, {'name': 'x', 'exercises': [{'sets': []}]}, write=True, now=NOW)
        self.assertFalse(out['ok'])
        self.assertEqual(db.store, {})

    def test_write_posts_once_and_refuses_overwrite(self):
        db = FakeDB()
        first = wilo_data.assign(db, MINIMAL, write=True, now=NOW)
        self.assertTrue(first['ok'])
        self.assertEqual(len(db.store), 1)
        again = wilo_data.assign(db, MINIMAL, write=True, now=NOW)
        self.assertFalse(again['ok'])
        self.assertIn('already exists', again['errors'][0])


if __name__ == '__main__':
    unittest.main()
