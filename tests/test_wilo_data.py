"""Tests for wilo/data.py. No Firestore access: assign() gets a fake db.

    .venv/bin/python -m unittest discover tests
"""

import unittest
from datetime import datetime, timezone

from wilo import data as wilo_data

NOW = datetime(2026, 10, 6, 11, 11, 56, 820000, tzinfo=timezone.utc)

MINIMAL = {'id': 'w1', 'name': 'legs', 'exercises': [
    {'name': 'squats', 'sets': [{'reps': 8, 'done': False}]}]}

# Shape the tracker writes today, extra fields included.
TRACKER = {'id': 'prog_1', 'name': 'legs-oct-6', 'finishedAt': '2026-10-06T13:16:29.498Z', 'exercises': [
    {'instanceId': 'ex1', 'exId': 'step-up', 'name': 'step up', 'timed': False, 'cue': '', 'note': 'felt good',
     'custom_name': 'Risers', 'fallback': None, 'swapped': False,
     'sets': [{'lbs': '', 'reps': 8, 'done': True, 'custom': '3'}, {'lbs': 30, 'reps': 6, 'done': False, 'custom': '4'}]}]}


class Snap:
    def __init__(self, key, data):
        self.id, self.exists, self._data = key.rsplit('/', 1)[-1], data is not None, data

    def to_dict(self):
        return self._data


class Ref:
    """A path in the fake store: works as a collection or a document, like the Firestore calls we use."""

    def __init__(self, store, path):
        self.store, self.path = store, path

    def collection(self, name):
        return Ref(self.store, f'{self.path}/{name}')

    def document(self, name):
        return Ref(self.store, f'{self.path}/{name}')

    def get(self):
        return Snap(self.path, self.store.get(self.path))

    def set(self, doc):
        self.store[self.path] = doc

    def stream(self):
        return [Snap(k, v) for k, v in self.store.items() if k.rsplit('/', 1)[0] == self.path]


class FakeDB:
    """Just enough of firestore.Client for assign, update, history and names. Docs live in a dict by path."""

    def __init__(self, docs=None):
        self.store = dict(docs or {})

    def collection(self, name):
        return Ref(self.store, name)


COMPLETED = f"users/{wilo_data.CONFIG['uid']}/completed"


def done(name, sets, finished):
    return {'id': finished, 'name': 'w', 'finishedAt': finished, 'exercises': [{'name': name, 'sets': sets}]}


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


class MatchTest(unittest.TestCase):
    def test_cosmetic_differences_match(self):
        pairs = [('push up', 'Pushups '), ('push up', 'Push-ups'), ('seated calf raise', 'calf raise seated'),
                 ('leg raise', 'Leg raises….'), ('crane', 'crane-plane'), ('single leg curl', 'single leg curls seated ')]
        for q, name in pairs:
            with self.subTest(q=q, name=name):
                self.assertTrue(wilo_data.name_matches(q, name))

    def test_different_exercises_dont_match(self):
        for q, name in [('bench', 'Barbell curl'), ('squat', 'step up'), ('press', 'Pushups ')]:
            with self.subTest(q=q, name=name):
                self.assertFalse(wilo_data.name_matches(q, name))


class HistoryNamesTest(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB({
            f'{COMPLETED}/a': done('Pushups ', [{'reps': 10, 'done': True}], '2026-10-01T22:36:00Z'),
            f'{COMPLETED}/b': done('Push-ups', [{'reps': 12, 'done': True}], '2026-10-08T17:00:00Z'),
            f'{COMPLETED}/c': done('Bench press', [{'lbs': 135, 'reps': 10, 'done': True}], '2026-10-08T17:00:00Z'),
            'completed/top-level': done('Push-ups', [{'reps': 99, 'done': True}], '2026-10-09T00:00:00Z'),
        })

    def test_history_newest_first_and_loose(self):
        h = wilo_data.history(self.db, 'push up', limit=5)
        self.assertEqual([x['name'] for x in h], ['Push-ups', 'Pushups '])  # top-level doc not included
        self.assertEqual(h[0]['sets'], [{'reps': 12, 'done': True}])

    def test_history_limit(self):
        self.assertEqual(len(wilo_data.history(self.db, 'push up', limit=1)), 1)

    def test_names_counts_and_last_done(self):
        n = {x['name']: x for x in wilo_data.names(self.db)}
        self.assertEqual(set(n), {'Pushups ', 'Push-ups', 'Bench press'})  # distinct as written; matching is Claude's job
        self.assertEqual(n['Push-ups']['lastDone'], '2026-10-08T17:00:00Z')


class UpdateTest(unittest.TestCase):
    def setUp(self):
        self.key = f'{COMPLETED}/oct5'
        self.old = done('Calf raise. ', [{'reps': 5, 'done': False}], '2026-10-05T13:22:00Z')
        self.db = FakeDB({self.key: self.old})
        self.new = {**self.old, 'docId': 'oct5', 'exercises': [{**self.old['exercises'][0], 'name': 'Seated calf raise'}]}

    def test_dry_run_shows_change_and_writes_nothing(self):
        out = wilo_data.update(self.db, 'completed', 'oct5', self.new, write=False)
        self.assertTrue(out['ok'] and out['dryRun'])
        self.assertEqual(out['changes'], ['exercises/0/name: "Calf raise. " -> "Seated calf raise"'])
        self.assertEqual(self.db.store[self.key], self.old)

    def test_write_saves_without_doc_id(self):
        out = wilo_data.update(self.db, 'completed', 'oct5', self.new, write=True)
        self.assertTrue(out['ok'])
        self.assertEqual(self.db.store[self.key]['exercises'][0]['name'], 'Seated calf raise')
        self.assertNotIn('docId', self.db.store[self.key])

    def test_refuses_missing_doc_changed_id_and_invalid(self):
        cases = {
            'missing doc': ('nope', self.new),
            'changed id': ('oct5', {**self.new, 'id': 'other'}),
            'invalid': ('oct5', {**self.new, 'exercises': [{'sets': []}]}),
        }
        for label, (doc_id, doc) in cases.items():
            with self.subTest(label):
                self.assertFalse(wilo_data.update(self.db, 'completed', doc_id, doc, write=True)['ok'])
                self.assertEqual(self.db.store[self.key], self.old)


if __name__ == '__main__':
    unittest.main()
