"""Tests for wilo/data.py. No Firestore access: the functions get a fake db.

    .venv/bin/python -m unittest discover tests
"""

import unittest
from datetime import datetime, timedelta, timezone

from wilo import data as wilo_data

NOW = datetime(2026, 10, 6, 11, 11, 56, 820000, tzinfo=timezone.utc)

MINIMAL = {'id': 'w1', 'name': 'legs', 'exercises': [
    {'name': 'squats', 'sets': [{'reps': 8, 'done': False}]}]}

# An exercise list the tracker writes as its log, extra fields included.
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

    def update(self, fields):
        if self.path not in self.store:
            raise KeyError(f'{self.path} not found')
        self.store[self.path] = {**self.store[self.path], **fields}

    def delete(self):
        self.store.pop(self.path, None)

    def stream(self):
        return [Snap(k, v) for k, v in self.store.items() if k.rsplit('/', 1)[0] == self.path]


class FakeDB:
    """Just enough of firestore.Client for assign, change, history and names. Docs live in a dict by path."""

    def __init__(self, docs=None):
        self.store = dict(docs or {})

    def collection(self, name):
        return Ref(self.store, name)


UID = 'thom'
OTHER = 'someone-else'
WORKOUTS = f'users/{UID}/workouts'


def done(name, sets, finished):
    """A finished workout logged with no plan: what history and names read."""
    return {'id': finished, 'name': 'w', 'status': 'done', 'finishedAt': finished, 'plan': [], 'diffs': [],
            'exercises': [], 'log': [{'exId': 'u-1', 'name': name, 'sets': sets}]}


class SchemaTest(unittest.TestCase):
    def test_accepts_planned_workout_and_a_stored_doc_with_a_tracker_log(self):
        self.assertEqual(wilo_data.validate(MINIMAL, 'plannedWorkout'), [])
        doc = {'id': 'w1', 'name': 'legs', 'status': 'in progress', 'plan': [], 'diffs': [], 'exercises': [],
               'log': TRACKER['exercises']}
        self.assertEqual(wilo_data.validate(doc), [])

    def test_accepts_blank_lbs_and_reps(self):
        doc = {**MINIMAL, 'exercises': [{'name': 'x', 'sets': [{'lbs': '', 'reps': '', 'done': False}]}]}
        self.assertEqual(wilo_data.validate(doc, 'plannedWorkout'), [])

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
                self.assertNotEqual(wilo_data.validate(doc, 'plannedWorkout'), [])

    def test_rejects_bad_ops(self):
        for op in [{'op': 'explode'}, {'op': 'remove'}, {'op': 'set', 'exId': 'x1', 'fields': {'log': []}},
                   {'op': 'move', 'exId': 'x1', 'to': -1}]:
            with self.subTest(op=op):
                self.assertNotEqual(wilo_data.validate(op, 'op'), [])


class AssignTest(unittest.TestCase):
    def test_doc_id_is_tracker_style(self):
        self.assertRegex(wilo_data.doc_id({'name': 'Pull Press'}, NOW), r'^\d{2}-[a-z]{3}-\d{2}:\d{2}-pull-$')

    def test_dry_run_writes_nothing_and_shows_the_doc(self):
        db = FakeDB()
        out = wilo_data.assign(db, UID, MINIMAL, write=False, now=NOW)
        self.assertTrue(out['ok'] and out['dryRun'])
        self.assertEqual(db.store, {})
        doc = out['doc']
        self.assertEqual((doc['status'], doc['diffs'], doc['log'], doc['nextExId']), ('planned', [], [], 2))
        self.assertEqual(doc['plan'], doc['exercises'])
        self.assertEqual(doc['plan'][0]['exId'], 'x1')
        self.assertEqual(doc['assignedFor'], '2026-10-06T11:11:56.820Z')  # filled when missing

    def test_plan_sets_are_never_done(self):
        w = {'name': 'x', 'exercises': [{'name': 'squat', 'sets': [{'reps': 5, 'done': True}]}]}
        self.assertFalse(wilo_data.assign(FakeDB(), UID, w, write=False, now=NOW)['doc']['plan'][0]['sets'][0]['done'])

    def test_invalid_workout_is_not_written(self):
        db = FakeDB()
        out = wilo_data.assign(db, UID, {'name': 'x', 'exercises': [{'sets': []}]}, write=True, now=NOW)
        self.assertFalse(out['ok'])
        self.assertEqual(db.store, {})

    def test_write_posts_once_and_refuses_overwrite(self):
        db = FakeDB()
        first = wilo_data.assign(db, UID, MINIMAL, write=True, now=NOW)
        self.assertTrue(first['ok'])
        self.assertEqual(list(db.store), [first['path']])
        self.assertTrue(first['path'].startswith(f'{WORKOUTS}/'))
        again = wilo_data.assign(db, UID, MINIMAL, write=True, now=NOW)
        self.assertFalse(again['ok'])
        self.assertIn('already exists', again['errors'][0])


LEGS = {'name': 'legs', 'assignedFor': '2026-10-08', 'exercises': [
    {'name': 'squat', 'cue': 'deep', 'sets': [{'lbs': 135, 'reps': 5, 'done': False}] * 3},
    {'name': 'leg curl', 'sets': [{'lbs': 50, 'reps': 10, 'done': False}] * 2},
    {'name': 'calf raise', 'sets': [{'reps': 15, 'done': False}] * 2}]}


class DiffTest(unittest.TestCase):
    """The coach changes a plan by adding a diff; the plan as it is now is apply_diffs(plan, diffs)."""

    def setUp(self):
        self.db = FakeDB()
        self.path = wilo_data.assign(self.db, UID, LEGS, write=True, now=NOW)['path']
        self.doc_id = self.path.rsplit('/', 1)[1]

    def change(self, ops, write=True):
        return wilo_data.change(self.db, UID, self.doc_id, ops, write, NOW)

    def names(self):
        return [x['name'] for x in self.db.store[self.path]['exercises']]

    def test_each_op(self):
        self.change([{'op': 'replace', 'exId': 'x1', 'exercise': {'name': 'leg press', 'sets': [{'lbs': 200, 'reps': 10, 'done': False}]}}])
        self.assertEqual(self.names(), ['leg press', 'leg curl', 'calf raise'])
        self.change([{'op': 'move', 'exId': 'x3', 'to': 0}, {'op': 'remove', 'exId': 'x2'}])
        self.assertEqual(self.names(), ['calf raise', 'leg press'])
        self.change([{'op': 'add', 'exercise': {'name': 'lunges', 'sets': [{'reps': 10, 'done': False}]}, 'at': 1},
                     {'op': 'set', 'exId': 'x3', 'fields': {'cue': 'slow', 'sets': [{'reps': 20, 'done': True}]}},
                     {'op': 'workout', 'name': 'legs (knee)', 'assignedFor': '2026-10-09'}])
        doc = self.db.store[self.path]
        self.assertEqual(self.names(), ['calf raise', 'lunges', 'leg press'])
        self.assertEqual([x['exId'] for x in doc['exercises']], ['x3', 'x5', 'x4'])  # new ones get new ids
        self.assertEqual(doc['exercises'][0]['cue'], 'slow')
        self.assertFalse(doc['exercises'][0]['sets'][0]['done'])  # a plan never says done
        self.assertEqual((doc['name'], doc['assignedFor']), ('legs (knee)', '2026-10-09'))
        self.assertEqual(len(doc['diffs']), 3)
        self.assertEqual(len(doc['plan']), 3)  # the plan as first written never changes
        self.assertEqual(wilo_data.apply_diffs(doc['plan'], doc['diffs'])[0], doc['exercises'])  # replay gives the same

    def test_dry_run_returns_the_new_plan_and_writes_nothing(self):
        before = dict(self.db.store[self.path])
        out = self.change([{'op': 'remove', 'exId': 'x1'}], write=False)
        self.assertTrue(out['ok'] and out['dryRun'])
        self.assertEqual([x['name'] for x in out['exercises']], ['leg curl', 'calf raise'])
        self.assertEqual(self.db.store[self.path], before)

    def test_never_touches_the_log(self):
        log = [{'exId': 'x1', 'name': 'squat', 'sets': [{'lbs': 135, 'reps': 5, 'done': True}]}]
        self.db.store[self.path] = {**self.db.store[self.path], 'log': log, 'logBase': 0, 'status': 'in progress'}
        self.change([{'op': 'remove', 'exId': 'x1'}])
        self.assertEqual(self.db.store[self.path]['log'], log)
        self.assertEqual(self.db.store[self.path]['status'], 'in progress')

    def test_refuses_unknown_exercise_bad_op_done_workout_and_missing_doc(self):
        before = dict(self.db.store[self.path])
        for label, ops in {'unknown exId': [{'op': 'remove', 'exId': 'x9'}], 'bad op': [{'op': 'explode'}],
                           'no ops': [], 'invalid result': [{'op': 'set', 'exId': 'x1', 'fields': {'sets': [{'reps': -1, 'done': False}]}}]}.items():
            with self.subTest(label):
                self.assertFalse(self.change(ops)['ok'])
                self.assertEqual(self.db.store[self.path], before)
        self.db.store[self.path] = {**before, 'status': 'done'}
        self.assertIn('is done', self.change([{'op': 'remove', 'exId': 'x1'}])['errors'][0])
        self.assertFalse(wilo_data.change(self.db, UID, 'nope', [{'op': 'remove', 'exId': 'x1'}], True, NOW)['ok'])


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
            f'{WORKOUTS}/a': done('Pushups ', [{'reps': 10, 'done': True}], '2026-10-01T22:36:00Z'),
            f'{WORKOUTS}/b': done('Push-ups', [{'reps': 12, 'done': True}], '2026-10-08T17:00:00Z'),
            f'{WORKOUTS}/c': done('Bench press', [{'lbs': 135, 'reps': 10, 'done': True}], '2026-10-08T17:00:00Z'),
            f'{WORKOUTS}/planned': {**done('Push-ups', [], ''), 'status': 'planned', 'log': []},
            'workouts/top-level': done('Push-ups', [{'reps': 99, 'done': True}], '2026-10-09T00:00:00Z'),
        })

    def test_history_newest_first_and_loose(self):
        h = wilo_data.history(self.db, UID, 'push up', limit=5)
        self.assertEqual([x['name'] for x in h], ['Push-ups', 'Pushups '])  # top-level and unlogged docs not included
        self.assertEqual(h[0]['sets'], [{'reps': 12, 'done': True}])

    def test_history_limit(self):
        self.assertEqual(len(wilo_data.history(self.db, UID, 'push up', limit=1)), 1)

    def test_deleted_exercises_are_not_history(self):
        self.db.store[f'{WORKOUTS}/b']['log'][0]['removed'] = True
        self.assertEqual([x['name'] for x in wilo_data.history(self.db, UID, 'push up', limit=5)], ['Pushups '])

    def test_names_counts_and_last_done(self):
        n = {x['name']: x for x in wilo_data.names(self.db, UID)}
        self.assertEqual(set(n), {'Pushups ', 'Push-ups', 'Bench press'})  # distinct as written; matching is Claude's job
        self.assertEqual(n['Push-ups']['lastDone'], '2026-10-08T17:00:00Z')

    def test_recent_filters_by_status(self):
        self.assertEqual([w['docId'] for w in wilo_data.recent(self.db, UID, 'planned', 5)], ['planned'])
        self.assertEqual(len(wilo_data.recent(self.db, UID, 'done', 2)), 2)


class IsolationTest(unittest.TestCase):
    """Each user only sees and writes their own data (the uid comes from the caller, never from the doc)."""

    def setUp(self):
        self.db = FakeDB({
            f'users/{UID}/workouts/a': done('Bench press', [{'lbs': 135, 'reps': 10, 'done': True}], '2026-10-01T00:00:00Z'),
            f'users/{OTHER}/workouts/b': done('Bench press', [{'lbs': 225, 'reps': 5, 'done': True}], '2026-10-02T00:00:00Z'),
        })

    def test_reads_only_own_data(self):
        self.assertEqual([h['sets'][0]['lbs'] for h in wilo_data.history(self.db, UID, 'bench', 5)], [135])
        self.assertEqual([h['sets'][0]['lbs'] for h in wilo_data.history(self.db, OTHER, 'bench', 5)], [225])
        self.assertEqual(len(wilo_data.names(self.db, OTHER)), 1)
        self.assertIs(wilo_data.get(self.db, OTHER, 'a').get('ok'), False)

    def test_writes_only_under_own_uid(self):
        before = set(self.db.store)
        wilo_data.assign(self.db, OTHER, MINIMAL, write=True, now=NOW)
        new = [k for k in self.db.store if k not in before]
        self.assertEqual(len(new), 1)
        self.assertTrue(new[0].startswith(f'users/{OTHER}/workouts/'))

    def test_cannot_change_another_users_workout(self):
        path = wilo_data.assign(self.db, UID, MINIMAL, write=True, now=NOW)['path']
        out = wilo_data.change(self.db, OTHER, path.rsplit('/', 1)[1], [{'op': 'remove', 'exId': 'x1'}], True, NOW)
        self.assertFalse(out['ok'])


class TodoTest(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.later = NOW.replace(minute=30)

    def add(self, text, uid=UID, now=NOW, **kw):
        return wilo_data.add_todo(self.db, uid, text, now, **kw)

    def test_add_saves_immediately_under_own_uid(self):
        out = self.add('  buy milk ', due='2026-10-12 19:00')
        self.assertTrue(out['ok'])
        self.assertEqual(self.db.store[f"users/{UID}/todos/{out['docId']}"],
                         {'text': 'buy milk', 'done': False, 'createdAt': '2026-10-06T11:11:56.820Z', 'due': '2026-10-12 19:00'})

    def test_add_refuses_empty_text_and_duplicate_id(self):
        self.assertFalse(self.add('  ')['ok'])
        self.add('a')
        self.assertFalse(self.add('b')['ok'])  # same millisecond, same id: refuse, don't overwrite
        self.assertEqual(len(self.db.store), 1)

    def test_list_open_first_dated_before_undated(self):
        self.add('undated old', now=NOW)
        self.add('later', now=NOW + timedelta(seconds=1), due='2026-10-13')
        self.add('sooner', now=NOW + timedelta(seconds=2), due='2026-10-12 19:00')
        self.add('undated new', now=NOW + timedelta(seconds=3))
        finished = self.add('finished', now=NOW + timedelta(seconds=4), due='2026-10-01')['docId']
        wilo_data.update_todo(self.db, UID, finished, {'done': True}, self.later)
        self.assertEqual([t['text'] for t in wilo_data.todos(self.db, UID)], ['sooner', 'later', 'undated old', 'undated new'])
        self.assertEqual(wilo_data.todos(self.db, UID, include_done=True)[-1]['text'], 'finished')

    def test_update_checks_off_reopens_and_clears(self):
        tid = self.add('call mum', due='2026-10-12', notes='about Sunday')['docId']
        out = wilo_data.update_todo(self.db, UID, tid, {'done': True, 'notes': ''}, self.later)
        self.assertEqual(out['todo']['doneAt'], '2026-10-06T11:30:56.820Z')
        self.assertNotIn('notes', out['todo'])
        self.assertEqual(out['todo']['due'], '2026-10-12')  # None/absent leaves it as is
        out = wilo_data.update_todo(self.db, UID, tid, {'done': False}, self.later)
        self.assertNotIn('doneAt', out['todo'])

    def test_update_refuses_missing_unknown_field_and_empty_text(self):
        tid = self.add('x')['docId']
        self.assertFalse(wilo_data.update_todo(self.db, UID, 'nope', {'done': True}, NOW)['ok'])
        self.assertFalse(wilo_data.update_todo(self.db, UID, tid, {'priority': 1}, NOW)['ok'])
        self.assertFalse(wilo_data.update_todo(self.db, UID, tid, {'text': ' '}, NOW)['ok'])
        self.assertEqual(self.db.store[f'users/{UID}/todos/{tid}']['text'], 'x')

    def test_delete(self):
        tid = self.add('x')['docId']
        self.assertTrue(wilo_data.delete_todo(self.db, UID, tid)['ok'])
        self.assertEqual(self.db.store, {})
        self.assertFalse(wilo_data.delete_todo(self.db, UID, tid)['ok'])

    def test_users_only_touch_their_own_todos(self):
        tid = self.add('mine')['docId']
        self.assertEqual(wilo_data.todos(self.db, OTHER), [])
        self.assertFalse(wilo_data.update_todo(self.db, OTHER, tid, {'done': True}, NOW)['ok'])
        self.assertFalse(wilo_data.delete_todo(self.db, OTHER, tid)['ok'])
        self.assertFalse(self.db.store[f'users/{UID}/todos/{tid}']['done'])



class ProfileTest(unittest.TestCase):
    PATH = f'users/{UID}/coach/profile'

    def setUp(self):
        self.db = FakeDB()

    def edit(self, write=False, uid=UID, **sections):
        return wilo_data.update_profile(self.db, uid, sections, write, NOW)

    def test_new_user_has_empty_profile(self):
        self.assertEqual(wilo_data.profile(self.db, UID),
                         {'exists': False, 'profile': dict.fromkeys(wilo_data.PROFILE_SECTIONS, ''), 'updatedAt': None})

    def test_dry_run_shows_changes_and_writes_nothing(self):
        out = self.edit(preferences='- no cues')
        self.assertEqual(out, {'ok': True, 'dryRun': True, 'path': self.PATH, 'changes': ['preferences: "" -> "- no cues"']})
        self.assertNotIn(self.PATH, self.db.store)

    def test_write_saves_and_left_out_sections_are_kept(self):
        self.edit(write=True, preferences='- no cues', limitations='- right shoulder: no bench')
        out = self.edit(write=True, notes='2026-10-10: loved the pump day')
        self.assertEqual(out['changes'], ['notes: "" -> "2026-10-10: loved the pump day"'])
        self.assertEqual(self.db.store[self.PATH], {'preferences': '- no cues', 'limitations': '- right shoulder: no bench',
                                                    'notes': '2026-10-10: loved the pump day',
                                                    'updatedAt': '2026-10-06T11:11:56.820Z'})
        p = wilo_data.profile(self.db, UID)
        self.assertTrue(p['exists'])
        self.assertEqual(p['profile']['plan'], '')

    def test_empty_string_clears_a_section(self):
        self.edit(write=True, preferences='- no cues', plan='PPL')
        self.edit(write=True, plan='')
        self.assertEqual(self.db.store[self.PATH]['preferences'], '- no cues')
        self.assertNotIn('plan', self.db.store[self.PATH])

    def test_refuses_unknown_sections_and_non_text(self):
        self.assertFalse(wilo_data.update_profile(self.db, UID, {'mood': 'x'}, True, NOW)['ok'])
        self.assertFalse(wilo_data.update_profile(self.db, UID, {'notes': ['x']}, True, NOW)['ok'])
        self.assertEqual(self.db.store, {})

    def test_users_only_touch_their_own_profile(self):
        self.edit(write=True, preferences='mine')
        self.edit(write=True, uid=OTHER, preferences='theirs')
        self.assertEqual(wilo_data.profile(self.db, UID)['profile']['preferences'], 'mine')
        self.assertEqual(wilo_data.profile(self.db, OTHER)['profile']['preferences'], 'theirs')


class ConnectTest(unittest.TestCase):
    """With no key file (Cloud Run), connect() uses the environment's own identity instead of a JSON key."""

    def connect_with(self, key_exists):
        from unittest import mock
        import firebase_admin
        from firebase_admin import credentials
        with mock.patch.object(firebase_admin, '_apps', {}), \
             mock.patch.object(firebase_admin, 'initialize_app') as init, \
             mock.patch('os.path.exists', return_value=key_exists), \
             mock.patch.object(credentials, 'Certificate') as cert, \
             mock.patch.object(credentials, 'ApplicationDefault') as adc, \
             mock.patch('firebase_admin.firestore.client'):
            wilo_data.connect()
        return init.call_args, cert, adc

    def test_no_key_file_uses_application_default_credentials(self):
        init, cert, adc = self.connect_with(key_exists=False)
        adc.assert_called_once()
        cert.assert_not_called()
        self.assertIs(init.args[0], adc.return_value)
        self.assertEqual(init.args[1], {'projectId': wilo_data.CONFIG['project']})

    def test_key_file_is_used_when_present(self):
        init, cert, adc = self.connect_with(key_exists=True)
        cert.assert_called_once()
        adc.assert_not_called()


if __name__ == '__main__':
    unittest.main()
