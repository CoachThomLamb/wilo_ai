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
TOOLS = {'workout_schema', 'recent_completed', 'recent_assigned', 'get_workout',
         'exercise_history', 'exercise_names', 'assign_workout', 'update_workout'}


def call(tool, **args):
    """Call a tool the way an MCP client does and return its JSON result."""
    res = asyncio.run(srv.server.call_tool(tool, args))
    if res.is_error:
        raise AssertionError(f'{tool} errored: {res.content}')
    return getattr(res, 'structured_content', None) or json.loads(res.content[0].text)


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB({
            f'users/{ME}/completed/a': done('Bench press', [{'lbs': 135, 'reps': 10, 'done': True}], '2026-10-01T00:00:00Z'),
            f'users/{OTHER}/completed/b': done('Bench press', [{'lbs': 225, 'reps': 5, 'done': True}], '2026-10-02T00:00:00Z'),
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

    def test_reads_act_on_current_user_only(self):
        self.assertEqual([h['sets'][0]['lbs'] for h in call('exercise_history', name='bench')['history']], [135])
        self.uid = OTHER
        self.assertEqual([h['sets'][0]['lbs'] for h in call('exercise_history', name='bench')['history']], [225])
        self.assertEqual([n['name'] for n in call('exercise_names')['names']], ['Bench press'])

    def test_get_workout_found_and_not_found(self):
        self.assertEqual(call('get_workout', collection='completed', doc_id='a')['docId'], 'a')
        self.assertFalse(call('get_workout', collection='completed', doc_id='b')['ok'])  # b is OTHER's

    def test_assign_is_a_dry_run_by_default(self):
        out = call('assign_workout', workout=MINIMAL)
        self.assertTrue(out['ok'] and out['dryRun'])
        self.assertFalse([k for k in self.db.store if '/assigned/' in k])

    def test_assign_write_lands_under_current_user(self):
        self.uid = OTHER
        self.assertTrue(call('assign_workout', workout=MINIMAL, write=True)['ok'])
        written = [k for k in self.db.store if '/assigned/' in k]
        self.assertEqual(len(written), 1)
        self.assertTrue(written[0].startswith(f'users/{OTHER}/assigned/'))

    def test_assign_rejects_invalid_workout(self):
        out = call('assign_workout', workout={'name': 'x', 'exercises': [{'sets': []}]}, write=True)
        self.assertFalse(out['ok'])
        self.assertTrue(any('name' in e for e in out['errors']))

    def test_update_is_a_dry_run_by_default(self):
        edited = {**self.db.store[f'users/{ME}/completed/a'], 'name': 'renamed'}
        out = call('update_workout', collection='completed', doc_id='a', workout=edited)
        self.assertTrue(out['ok'] and out['dryRun'])
        self.assertEqual(out['changes'], ['name: "w" -> "renamed"'])
        self.assertEqual(self.db.store[f'users/{ME}/completed/a']['name'], 'w')

    def test_bad_collection_is_rejected_by_mcp(self):
        with self.assertRaises(ToolError):
            asyncio.run(srv.server.call_tool('get_workout', {'collection': 'programs', 'doc_id': 'a'}))


if __name__ == '__main__':
    unittest.main()
