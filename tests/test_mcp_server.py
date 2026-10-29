"""Tests for wilo/mcp_server.py: the tools as Claude calls them, through the MCP layer. No Firestore: a fake db.

    .venv/bin/python -m unittest discover tests
"""

import asyncio
import json
import unittest

from mcp.server.mcpserver.exceptions import ToolError
from test_wilo_data import FakeDB, MINIMAL, done

from wilo import mcp_server as srv

ME, OTHER = 'thom', 'someone-else'
TOOLS = {'coaching_method', 'get_profile', 'update_profile', 'workout_schema', 'recent_workouts', 'get_workout',
         'exercise_history', 'exercise_names', 'assign_workout', 'change_workout',
         'list_todos', 'add_todo', 'update_todo', 'delete_todo'}


def call(tool, **args):
    """Call a tool the way an MCP client does and return its JSON result."""
    res = asyncio.run(srv.server.call_tool(tool, args))
    if res.is_error:
        raise AssertionError(f'{tool} errored: {res.content}')
    return getattr(res, 'structured_content', None) or json.loads(res.content[0].text)


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB({
            f'users/{ME}/workouts/a': done('Bench press', [{'lbs': 135, 'reps': 10, 'done': True}], '2026-10-01T00:00:00Z'),
            f'users/{OTHER}/workouts/b': done('Bench press', [{'lbs': 225, 'reps': 5, 'done': True}], '2026-10-02T00:00:00Z'),
        })
        self.uid = ME
        self._saved = srv.db, srv.current_uid
        srv.db, srv.current_uid = (lambda: self.db), (lambda: self.uid)

    def tearDown(self):
        srv.db, srv.current_uid = self._saved

    def test_tools_listed_and_none_take_a_uid(self):
        tools = asyncio.run(srv.server.list_tools())
        self.assertEqual({t.name for t in tools}, TOOLS)
        for t in tools:
            schema = getattr(t, 'input_schema', None) or getattr(t, 'inputSchema', {})
            with self.subTest(t.name):
                self.assertNotIn('uid', json.dumps(schema).lower())

    def test_schema_tool_returns_the_schema_file(self):
        self.assertEqual(call('workout_schema')['title'], 'WILO workout')

    def test_coaching_method_returns_the_method_file(self):
        self.assertEqual(call('coaching_method')['method'], (srv.HERE / 'coach.md').read_text())

    def test_reads_act_on_current_user_only(self):
        self.assertEqual([h['sets'][0]['lbs'] for h in call('exercise_history', name='bench')['history']], [135])
        self.uid = OTHER
        self.assertEqual([h['sets'][0]['lbs'] for h in call('exercise_history', name='bench')['history']], [225])
        self.assertEqual([n['name'] for n in call('exercise_names')['names']], ['Bench press'])

    def test_get_workout_found_and_not_found(self):
        self.assertEqual(call('get_workout', doc_id='a')['docId'], 'a')
        self.assertFalse(call('get_workout', doc_id='b')['ok'])  # b is OTHER's

    def test_recent_workouts_by_status(self):
        self.assertEqual([w['docId'] for w in call('recent_workouts', status='done')['workouts']], ['a'])
        self.assertEqual(call('recent_workouts', status='planned')['workouts'], [])

    def test_assign_is_a_dry_run_by_default(self):
        before = dict(self.db.store)
        out = call('assign_workout', workout=MINIMAL)
        self.assertTrue(out['ok'] and out['dryRun'])
        self.assertEqual(self.db.store, before)

    def test_assign_write_lands_under_current_user(self):
        self.uid = OTHER
        before = set(self.db.store)
        self.assertTrue(call('assign_workout', workout=MINIMAL, write=True)['ok'])
        written = [k for k in self.db.store if k not in before]
        self.assertEqual(len(written), 1)
        self.assertTrue(written[0].startswith(f'users/{OTHER}/workouts/'))

    def test_assign_rejects_invalid_workout(self):
        out = call('assign_workout', workout={'name': 'x', 'exercises': [{'sets': []}]}, write=True)
        self.assertFalse(out['ok'])
        self.assertTrue(any('name' in e for e in out['errors']))

    def test_change_is_a_dry_run_by_default_then_writes(self):
        path = call('assign_workout', workout=MINIMAL, write=True)['path']
        doc_id = path.rsplit('/', 1)[1]
        ops = [{'op': 'set', 'exId': 'x1', 'fields': {'name': 'front squat'}}]
        out = call('change_workout', doc_id=doc_id, ops=ops)
        self.assertTrue(out['ok'] and out['dryRun'])
        self.assertEqual(out['exercises'][0]['name'], 'front squat')
        self.assertEqual(self.db.store[path]['exercises'][0]['name'], 'squats')
        self.assertTrue(call('change_workout', doc_id=doc_id, ops=ops, write=True)['ok'])
        self.assertEqual(self.db.store[path]['exercises'][0]['name'], 'front squat')

    def test_bad_status_is_rejected_by_mcp(self):
        with self.assertRaises(ToolError):
            asyncio.run(srv.server.call_tool('recent_workouts', {'status': 'completed'}))

    def test_todos_round_trip_for_current_user_only(self):
        tid = call('add_todo', text='stretch', due='2026-10-12 07:00')['docId']
        self.assertTrue(f'users/{ME}/todos/{tid}' in self.db.store)  # no dry run: saved straight away
        self.assertEqual([t['text'] for t in call('list_todos')['todos']], ['stretch'])
        self.assertTrue(call('update_todo', doc_id=tid, done=True)['todo']['done'])
        self.assertEqual(call('list_todos')['todos'], [])
        self.uid = OTHER
        self.assertFalse(call('delete_todo', doc_id=tid)['ok'])
        self.uid = ME
        self.assertTrue(call('delete_todo', doc_id=tid)['ok'])

    def test_profile_is_a_dry_run_by_default_and_per_user(self):
        path = f'users/{ME}/coach/profile'
        self.assertFalse(call('get_profile')['exists'])
        dry = call('update_profile', preferences='- no cues')
        self.assertTrue(dry['dryRun'])
        self.assertNotIn(path, self.db.store)
        call('update_profile', preferences='- no cues', write=True)
        self.assertEqual(call('get_profile')['profile']['preferences'], '- no cues')
        self.uid = OTHER
        self.assertFalse(call('get_profile')['exists'])

    def test_method_covers_profile_and_safety(self):
        method = call('coaching_method')['method']
        for needle in ('get_profile', 'update_profile', 'except on safety', 'Load keeps the sets'):
            with self.subTest(needle):
                self.assertIn(needle, method)


if __name__ == '__main__':
    unittest.main()
