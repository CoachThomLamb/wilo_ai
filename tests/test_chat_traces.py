"""Tests for the chat trace facade (wilo.data.chat_traces) and coaching-evals/export_tracker_chats.py (#112).
No Firestore: a fake db from test_wilo_data.

    .venv/bin/python -m unittest discover tests
"""

import copy
import importlib.util
import json
import unittest
from pathlib import Path

from test_wilo_data import FakeDB

from wilo import data as wilo_data

spec = importlib.util.spec_from_file_location(
    'export_tracker_chats', Path(__file__).resolve().parent.parent / 'coaching-evals' / 'export_tracker_chats.py')
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)

# One chat turn as chat.py stores it: the user's text, a reply with thinking + a tool call, the tool result, the answer.
TURN = [
    {'role': 'user', 'content': 'plan back day'},
    {'role': 'assistant', 'content': [{'type': 'thinking', 'thinking': '', 'signature': 's'},
                                      {'type': 'text', 'text': 'Checking your history.'},
                                      {'type': 'tool_use', 'id': 't1', 'name': 'recent_completed', 'input': {'limit': 5}}]},
    {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 't1', 'content': '{"workouts": []}'}]},
    {'role': 'assistant', 'content': [{'type': 'text', 'text': 'Rows and pulldowns today. Good?'}]},
]
TURN2 = [{'role': 'user', 'content': 'yes'}, {'role': 'assistant', 'content': [{'type': 'text', 'text': 'Saved.'}]}]


def store():
    return {
        'chat_threads/b': {'uid': 'thom', 'createdAt': '2026-10-24T10:00:00+00:00', 'context': 'Today is Friday'},
        'chat_threads/b/turns/0001': {'messages': json.dumps(TURN), 'at': '2026-10-24T10:00:05+00:00'},
        'chat_threads/b/turns/0002': {'messages': json.dumps(TURN2), 'at': '2026-10-24T10:02:00+00:00'},
        'chat_threads/a': {'uid': 'thom', 'createdAt': '2026-10-23T09:00:00+00:00', 'context': ''},
        'chat_threads/c': {'uid': 'someone-else', 'createdAt': '2026-10-24T11:00:00+00:00', 'context': ''},
    }


class FacadeTest(unittest.TestCase):
    def test_reads_one_users_chats_oldest_first_with_turns_in_order(self):
        traces = wilo_data.chat_traces(FakeDB(store()), uid='thom')
        self.assertEqual([t['chatId'] for t in traces], ['a', 'b'])
        b = traces[1]
        self.assertEqual((b['uid'], b['context']), ('thom', 'Today is Friday'))
        self.assertEqual([t['at'][11:16] for t in b['turns']], ['10:00', '10:02'])
        self.assertEqual(b['turns'][0]['messages'], TURN)

    def test_without_uid_reads_everyone(self):
        self.assertEqual(len(wilo_data.chat_traces(FakeDB(store()))), 3)

    def test_never_writes(self):
        db = FakeDB(store())
        before = copy.deepcopy(db.store)
        wilo_data.chat_traces(db)
        self.assertEqual(db.store, before)


class ExportTest(unittest.TestCase):
    def trace(self, docs=None):
        return export.to_trace(wilo_data.chat_traces(FakeDB(docs or store()), uid='thom')[1])

    def test_one_user_message_then_one_reply_with_its_tool_calls(self):
        t = self.trace()
        self.assertEqual((t['id'], t['source'], t['label'], t['title']), ('b', 'tracker', 'coaching', 'plan back day'))
        self.assertEqual([m['role'] for m in t['messages']], ['user', 'assistant', 'user', 'assistant'])
        reply = t['messages'][1]
        self.assertEqual(reply['content'], 'Checking your history.\n\nRows and pulldowns today. Good?')
        self.assertEqual(reply['tool_calls'], [{'name': 'recent_completed', 'args': {'limit': 5}}])
        self.assertNotIn('thinking', json.dumps(t['messages']))
        self.assertNotIn('tool_result', json.dumps(t['messages']))
        self.assertEqual(t['updated_at'], '2026-10-24T10:02:00+00:00')

    def test_a_new_turn_keeps_earlier_message_indexes(self):
        """notes.json is keyed by message index, so a growing chat must not shift earlier messages."""
        before = self.trace()['messages']
        docs = store()
        docs['chat_threads/b/turns/0003'] = {'messages': json.dumps(TURN2), 'at': '2026-10-24T10:05:00+00:00'}
        self.assertEqual(self.trace(docs)['messages'][:len(before)], before)


if __name__ == '__main__':
    unittest.main()
