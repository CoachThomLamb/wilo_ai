"""Tests for wilo/pg.py on a real Postgres: what the shared suite can't show (merge, Increment under concurrency,
update's NotFound, paths, migrations, dual-write, backfill). Skipped unless WILO_TEST_DATABASE_URL is set (see
tests/pg_fake.py); the parts that need no database (WILO_DB, path map, values) always run.

    WILO_TEST_DATABASE_URL=postgresql://postgres:test@127.0.0.1:55432/postgres .venv/bin/python -m unittest discover -s tests
"""

import os
import threading
import unittest
from datetime import datetime, timezone
from unittest import mock

from google.api_core.exceptions import NotFound
from google.cloud.firestore import Increment
from test_wilo_data import MemoryDB, Ref

from wilo import data as wilo_data
from wilo import pg

URL = os.environ.get('WILO_TEST_DATABASE_URL')


class NoDatabaseTest(unittest.TestCase):
    def test_locate(self):
        self.assertEqual(pg.locate('users'), ('users', {}))
        self.assertEqual(pg.locate('users/u1/workouts'), ('workouts', {'uid': 'u1'}))
        self.assertEqual(pg.locate('users/u1/coach'), ('coach', {'uid': 'u1'}))
        self.assertEqual(pg.locate('chat_threads/c1/turns'), ('chat_turns', {'chat_id': 'c1'}))
        self.assertEqual(pg.locate('users/u1/assigned'), ('documents', {'collection': 'users/u1/assigned'}))
        self.assertEqual(pg.locate('oauth_codes'), ('documents', {'collection': 'oauth_codes'}))
        for bad in ('', 'users/u1', 'users//workouts'):
            with self.assertRaises(ValueError):
                pg.locate(bad)

    def test_plain_values(self):
        at = datetime(2026, 11, 25, 21, 0, 0, 123456, tzinfo=timezone.utc)
        self.assertEqual(pg.plain({'at': at, 'xs': (1, b'hi')}), {'at': '2026-11-25T21:00:00.123Z', 'xs': [1, 'aGk=']})

    def test_backend_choice(self):
        with mock.patch.dict(os.environ, {'WILO_DB': 'mongo'}):
            with self.assertRaises(ValueError):
                wilo_data.backend()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('WILO_DB', None)
            self.assertEqual(wilo_data.backend(), 'firestore')

    def test_postgres_needs_a_url(self):
        with mock.patch.dict(os.environ, {'DATABASE_URL': ''}):
            with self.assertRaises(RuntimeError):
                wilo_data.postgres_client()


# ---- a Firestore stand-in for backfill: the in-memory fake plus collections(), list_documents() and count() ----

class FsRef(Ref):
    def collection(self, name):
        return FsRef(self.store, f'{self.path}/{name}')

    def document(self, name):
        return FsRef(self.store, f'{self.path}/{name}')

    @property
    def id(self):
        return self.path.rsplit('/', 1)[-1]

    def _below(self):
        return [k[len(self.path) + 1:].split('/') for k in self.store if k.startswith(self.path + '/')]

    def list_documents(self):  # docs and parents of subcollections
        return [self.document(i) for i in sorted({p[0] for p in self._below()})]

    def collections(self):
        return [self.collection(c) for c in sorted({p[0] for p in self._below() if len(p) >= 2})]

    def count(self):
        n = len(self.stream())
        agg = type('Agg', (), {'value': n})()
        return type('Q', (), {'get': lambda _: [[agg]]})()


class FakeFirestore(MemoryDB):
    def collection(self, name):
        return FsRef(self.store, name)

    def collections(self):
        return [self.collection(c) for c in sorted({k.split('/')[0] for k in self.store})]


@unittest.skipUnless(URL, 'set WILO_TEST_DATABASE_URL to a throwaway Postgres')
class PostgresTest(unittest.TestCase):
    def setUp(self):
        from pg_fake import FakeDB
        self.db = FakeDB()

    def test_round_trip_and_order(self):
        ws = self.db.collection('users').document('u1').collection('workouts')
        ws.document('b').set({'n': 2, 'nested': {'x': [1, {'y': None}]}})
        ws.document('A:1').set({'n': 1})
        self.assertEqual(ws.document('b').get().to_dict(), {'n': 2, 'nested': {'x': [1, {'y': None}]}})
        self.assertEqual([s.id for s in ws.stream()], ['A:1', 'b'])  # by doc id, bytewise, like Firestore
        self.assertFalse(ws.document('zz').get().exists)
        self.assertIsNone(ws.document('zz').get().to_dict())
        ws.document('b').delete()
        self.assertEqual([s.id for s in ws.stream()], ['A:1'])

    def test_set_replaces_merge_merges_deep(self):
        ref = self.db.collection('chat_feedback').document('c1')
        ref.set({'a': 1, 'm': {'x': 1, 'y': 1}})
        ref.set({'m': {'y': 2}, 'b': 2}, merge=True)
        self.assertEqual(ref.get().to_dict(), {'a': 1, 'b': 2, 'm': {'x': 1, 'y': 2}})
        ref.set({'c': 3})
        self.assertEqual(ref.get().to_dict(), {'c': 3})

    def test_increment_is_atomic(self):
        ref = self.db.collection('chat_spend').document('u1')

        def add():
            for _ in range(10):
                ref.set({'uid': 'u1', 'usd': Increment(0.5)}, merge=True)
        threads = [threading.Thread(target=add) for _ in range(4)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(ref.get().to_dict(), {'uid': 'u1', 'usd': 20.0})

    def test_update(self):
        ref = self.db.collection('users').document('u1').collection('workouts').document('w')
        with self.assertRaises(NotFound):
            ref.update({'status': 'done'})
        ref.set({'status': 'planned', 'log': [1], 'm': {'a': 1, 'b': 1}})
        ref.update({'status': 'done', 'm.b': 2, 'm.c.d': 3})
        self.assertEqual(ref.get().to_dict(), {'status': 'done', 'log': [1], 'm': {'a': 1, 'b': 2, 'c': {'d': 3}}})

    def test_generated_columns(self):
        ref = self.db.collection('users').document('u1').collection('workouts').document('w')
        ref.set({'status': 'planned', 'assignedFor': '2026-11-26T12:00:00Z'})
        with self.db.pool.connection() as conn:
            row = conn.execute("SELECT status, assigned_for FROM workouts WHERE uid = 'u1'").fetchone()
        self.assertEqual(row, ('planned', '2026-11-26T12:00:00Z'))

    def test_list_users_includes_users_with_only_subcollections(self):
        users = self.db.collection('users')
        users.document('has-doc').set({'email': 'x'})
        users.document('only-workouts').collection('workouts').document('w').set({})
        users.document('only-backup').collection('assigned').document('a').set({})
        self.assertEqual([d.id for d in users.list_documents()], ['has-doc', 'only-backup', 'only-workouts'])

    def test_replace_collection_mirrors(self):
        todos = self.db.collection('users').document('u1').collection('todos')
        todos.document('old').set({'t': 'gone'})
        todos.document('keep').set({'t': 1})
        self.db.collection('users').document('u2').collection('todos').document('other').set({'t': 'untouched'})
        self.db.replace_collection('users/u1/todos', {'keep': {'t': 2}, 'new': {'t': 3}})
        self.assertEqual({s.id: s.to_dict() for s in todos.stream()}, {'keep': {'t': 2}, 'new': {'t': 3}})
        self.assertTrue(self.db.collection('users').document('u2').collection('todos').document('other').get().exists)

    def test_migrations_apply_once(self):
        with self.db.pool.connection() as conn:
            pg.migrate(conn)
            pg.migrate(conn)
            self.assertEqual(conn.execute('SELECT count(*) FROM schema_migrations').fetchone()[0],
                             len(list(pg.MIGRATIONS.glob('*.sql'))))

    def test_dual_reads_firestore_and_copies_every_write(self):
        fs = MemoryDB({'users/u1/workouts/old': {'n': 0}})
        dual = pg.Dual(fs, self.db)
        ws = dual.collection('users').document('u1').collection('workouts')
        ws.document('w').set({'n': 1, 'usd': Increment(2)})
        ws.document('w').update({'n': 2})
        ws.document('old').set({'n': 9}, merge=True)  # never copied before: the copy is the whole Firestore doc
        pgw = self.db.collection('users').document('u1').collection('workouts')
        self.assertEqual(pgw.document('w').get().to_dict(), {'n': 2, 'usd': 2})
        self.assertEqual(pgw.document('old').get().to_dict(), {'n': 9})
        self.db.collection('users').document('u1').collection('workouts').document('pg-only').set({'n': 7})
        self.assertEqual(sorted(s.id for s in ws.stream()), ['old', 'w'])  # reads are Firestore's
        ws.document('w').delete()
        self.assertFalse(pgw.document('w').get().exists)

    def test_dual_survives_postgres_failing(self):
        fs = MemoryDB()
        broken = mock.Mock()
        broken.collection.side_effect = lambda n: BrokenRef()
        dual = pg.Dual(fs, broken)
        with mock.patch('builtins.print'):
            dual.collection('todos').document('t').set({'a': 1})
        self.assertEqual(fs.store['todos/t'], {'a': 1})

    def test_backfill(self):
        at = datetime(2026, 11, 1, tzinfo=timezone.utc)
        fs = FakeFirestore({
            'users/u1': {'email': 'a', 'lastSignIn': at},
            'users/u1/workouts/w1': {'status': 'done'},
            'users/u1/coach/records': {'exercises': {}},
            'users/u2/assigned/x': {'old': True},
            'chat_threads/c1': {'uid': 'u1'},
            'chat_threads/c1/turns/0001': {'messages': '[]'},
            'chat_spend/u1': {'usd': 1.5},
            'oauth_codes/k': {'uid': 'u1'},
        })
        self.db.collection('users').document('u1').collection('workouts').document('stale').set({'gone': True})
        dry = pg.backfill(fs, None, write=False)
        self.assertEqual(dry['docs'], 8)
        self.assertEqual(dry['collections']['users/*/workouts'], 1)
        self.assertNotIn('u1', str(dry['collections']))  # no uids in the summary
        self.assertFalse(self.db.collection('users').document('u1').get().exists)  # a dry run writes nothing
        out = pg.backfill(fs, self.db, write=True)
        self.assertTrue(out['ok'])
        self.assertEqual(dict(self.db.store), {
            'users/u1': {'email': 'a', 'lastSignIn': '2026-11-01T00:00:00.000Z'},
            'users/u1/workouts/w1': {'status': 'done'},
            'users/u1/coach/records': {'exercises': {}},
            'users/u2/assigned/x': {'old': True},
            'chat_threads/c1': {'uid': 'u1'},
            'chat_threads/c1/turns/0001': {'messages': '[]'},
            'chat_spend/u1': {'usd': 1.5},
            'oauth_codes/k': {'uid': 'u1'},
        })
        with mock.patch.object(pg, 'READ_BUDGET', 3):
            self.assertFalse(pg.backfill(fs, self.db, write=True)['ok'])
            self.assertTrue(pg.backfill(fs, self.db, write=True, force=True)['ok'])


class BrokenRef:
    def document(self, _):
        return self

    def collection(self, _):
        return self

    def set(self, *a, **k):
        raise ConnectionError('postgres is down')

    path = 'todos/t'


if __name__ == '__main__':
    unittest.main()
