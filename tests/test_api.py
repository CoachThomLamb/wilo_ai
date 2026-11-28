"""Tests for wilo/api.py: the tracker's data routes over HTTP, in-process, on the fake db (or Postgres, see
tests/pg_fake.py) with a stubbed token check.

    .venv/bin/python -m unittest discover tests
"""

import unittest

import firebase_admin.auth
from starlette.testclient import TestClient
from test_wilo_data import FakeDB, MINIMAL, done

from wilo import data as wilo_data
from wilo import mcp_server as srv

ME, OTHER = 'thom', 'someone-else'
TOKENS = {'my-token': ME, 'other-token': OTHER}
TRACKER = 'https://wilo2-1ee44.web.app'
MINE = f'users/{ME}/workouts'


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB({
            f'{MINE}/a': done('Bench press', [{'lbs': 135, 'reps': 10, 'done': True}], '2026-10-01T00:00:00Z'),
            f'{MINE}/p': {**MINIMAL, 'status': 'planned', 'assignedFor': '2026-10-05T12:00:00Z', 'plan': [], 'diffs': [],
                          'log': [], 'logBase': 0},
            f'users/{OTHER}/workouts/b': done('Bench press', [{'lbs': 225, 'reps': 5, 'done': True}], '2026-10-02T00:00:00Z'),
        })
        self.saved = srv.db, firebase_admin.auth.verify_id_token
        srv.db = lambda: self.db
        firebase_admin.auth.verify_id_token = lambda tok: {'uid': TOKENS[tok]}
        self.http = TestClient(srv.make_server().streamable_http_app()).__enter__()

    def tearDown(self):
        self.http.__exit__(None, None, None)
        srv.db, firebase_admin.auth.verify_id_token = self.saved

    def call(self, method, path, body=None, token='my-token'):
        return self.http.request(method, path, json=body,
                                 headers={'Authorization': f'Bearer {token}', 'Origin': TRACKER})

    def test_needs_sign_in(self):
        self.assertEqual(self.http.get('/api/workouts').status_code, 401)
        self.assertEqual(self.call('GET', '/api/workouts', token='forged').status_code, 401)

    def test_preflight_and_cors_only_for_the_tracker(self):
        r = self.http.options('/api/workouts/a', headers={'Origin': TRACKER})
        self.assertEqual(r.status_code, 204)
        self.assertIn('PATCH', r.headers['access-control-allow-methods'])
        r = self.http.get('/api/workouts', headers={'Authorization': 'Bearer my-token', 'Origin': 'https://evil.example'})
        self.assertNotIn('access-control-allow-origin', r.headers)

    def test_lists_only_my_workouts_newest_first_and_by_day(self):
        ids = [w['docId'] for w in self.call('GET', '/api/workouts').json()['workouts']]
        self.assertEqual(sorted(ids), ['a', 'p'])
        r = self.call('GET', '/api/workouts?from=2026-10-05&to=2026-10-05').json()
        self.assertEqual([w['docId'] for w in r['workouts']], ['p'])
        self.assertEqual(self.call('GET', '/api/workouts?from=yesterday').status_code, 400)

    def test_get_one_and_never_someone_elses(self):
        self.assertEqual(self.call('GET', '/api/workouts/a').json()['docId'], 'a')
        self.assertEqual(self.call('GET', '/api/workouts/b').status_code, 404)
        self.assertEqual(self.call('GET', '/api/workouts/b', token='other-token').status_code, 200)

    def test_patch_saves_the_log_and_nothing_else(self):
        log = [{'name': 'squats', 'sets': [{'reps': 8, 'done': True}]}]
        r = self.call('PATCH', '/api/workouts/p', {'log': log, 'status': 'in progress', 'updatedAt': '2026-10-05T13:00:00Z'})
        self.assertEqual(r.status_code, 200, r.text)
        doc = self.db.store[f'{MINE}/p']
        self.assertEqual((doc['log'], doc['status'], doc['name']), (log, 'in progress', 'legs'))
        self.assertEqual(self.call('PATCH', '/api/workouts/p', {'exercises': []}).status_code, 400)  # the plan is the coach's
        self.assertEqual(self.call('PATCH', '/api/workouts/p', {'status': 'deleted'}).status_code, 400)
        self.assertEqual(self.db.store[f'{MINE}/p']['exercises'], MINIMAL['exercises'])

    def test_patch_missing_is_404_so_the_tracker_creates_it(self):
        self.assertEqual(self.call('PATCH', '/api/workouts/new', {'status': 'done'}).status_code, 404)
        self.assertEqual(self.call('PATCH', '/api/workouts/b', {'status': 'done'}).status_code, 404)  # not mine
        self.assertEqual(self.db.store['users/someone-else/workouts/b']['status'], 'done')
        self.assertNotIn('rating', self.db.store['users/someone-else/workouts/b'])

    def test_put_creates_a_logged_workout_once(self):
        doc = {'id': 'log_1', 'name': 'Workout', 'assignedFor': '2026-10-06T10:00:00Z', 'createdAt': '2026-10-06T10:00:00Z',
               'plan': [], 'diffs': [], 'exercises': [], 'log': [], 'logBase': 0, 'status': 'in progress',
               'updatedAt': '2026-10-06T10:00:00Z'}
        self.assertEqual(self.call('PUT', '/api/workouts/06-oct-10:00-worko', doc).status_code, 201)
        self.assertEqual(self.db.store[f'{MINE}/06-oct-10:00-worko']['status'], 'in progress')
        self.assertEqual(self.call('PUT', '/api/workouts/06-oct-10:00-worko', doc).status_code, 409)
        self.assertEqual(self.call('PUT', '/api/workouts/x', {**doc, 'exercises': MINIMAL['exercises']}).status_code, 400)
        self.assertEqual(self.call('PUT', '/api/workouts/y', {**doc, 'status': 'planned'}).status_code, 400)

    def test_records_round_trip(self):
        self.assertEqual(self.call('GET', '/api/records').json(), {})
        ex = {'bench|': [{'lbs': 135, 'reps': 10}]}
        self.assertEqual(self.call('PUT', '/api/records', {'exercises': ex}).status_code, 200)
        self.assertEqual(self.call('GET', '/api/records').json()['exercises'], ex)
        self.assertEqual(self.call('GET', '/api/records', token='other-token').json(), {})
        self.assertEqual(self.call('PUT', '/api/records', {'exercises': {'bench|': [[135, 10]]}}).status_code, 400)
        self.assertEqual(self.call('PUT', '/api/records', ['nope']).status_code, 400)


class TrackerDataTest(unittest.TestCase):
    def test_save_log_refuses_plan_fields(self):
        db = FakeDB({f'{MINE}/p': {'name': 'x', 'status': 'planned'}})
        out = wilo_data.save_log(db, ME, 'p', {'plan': []})
        self.assertFalse(out['ok'])
        self.assertEqual(db.store[f'{MINE}/p'], {'name': 'x', 'status': 'planned'})


if __name__ == '__main__':
    unittest.main()
