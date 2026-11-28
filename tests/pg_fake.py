"""FakeDB on a real Postgres (#241): the whole test suite runs against wilo/pg.py when WILO_TEST_DATABASE_URL is
set, so every test that passes on the in-memory fake also proves the Postgres backend behaves the same.

    docker run -d --rm --name wilo-pg-test -e POSTGRES_PASSWORD=test -p 127.0.0.1:55432:5432 postgres:17-alpine
    WILO_TEST_DATABASE_URL=postgresql://postgres:test@127.0.0.1:55432/postgres .venv/bin/python -m unittest discover -s tests

The database is emptied for each FakeDB: never point this at a real one.
"""

import atexit
import os
from collections.abc import MutableMapping

from wilo import pg

_client = None


def client():
    global _client
    if _client is None:
        _client = pg.Client(os.environ['WILO_TEST_DATABASE_URL'], max_size=2)
        atexit.register(_client.close)
    return _client


def _split(path):
    coll, doc_id = path.rsplit('/', 1)
    return coll, doc_id


class PgStore(MutableMapping):
    """{path: doc} over the tables, like the in-memory fake's store, so tests can seed and inspect it."""

    def __init__(self, c):
        self.c = c

    def __getitem__(self, path):
        doc = self.c.read(*_split(path))
        if doc is None:
            raise KeyError(path)
        return doc

    def __setitem__(self, path, doc):
        self.c.write(*_split(path), doc)

    def __delitem__(self, path):
        if path not in self:
            raise KeyError(path)
        self.c.delete(*_split(path))

    def __contains__(self, path):
        return isinstance(path, str) and '/' in path and self.c.read(*_split(path)) is not None

    def __iter__(self):
        with self.c.pool.connection() as conn:
            paths = [f'users/{k}' for (k,) in conn.execute('SELECT doc_id FROM users')]
            for t in pg.USER_SUBS:
                paths += [f'users/{u}/{t}/{k}' for u, k in conn.execute(f'SELECT uid, doc_id FROM {t}')]
            for t in pg.TOP[1:]:
                paths += [f'{t}/{k}' for (k,) in conn.execute(f'SELECT doc_id FROM {t}')]
            for sub, t in pg.THREAD_SUBS.items():
                paths += [f'chat_threads/{c}/{sub}/{k}' for c, k in conn.execute(f'SELECT chat_id, doc_id FROM {t}')]
            paths += [f'{c}/{k}' for c, k in conn.execute('SELECT collection, doc_id FROM documents')]
        return iter(sorted(paths))

    def __len__(self):
        return sum(1 for _ in self)


class FakeDB(pg.Client):
    """A pg.Client on the test database, emptied and seeded with docs ({path: doc})."""

    def __init__(self, docs=None):
        c = client()
        self.pool = c.pool
        self.truncate_all()
        self.store = PgStore(self)
        for path, doc in (docs or {}).items():
            self.store[path] = doc
