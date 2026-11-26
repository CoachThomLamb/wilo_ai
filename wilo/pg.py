"""
Postgres backend (#241): the slice of the Firestore client API that wilo/data.py, chat.py, auth.py and media.py
use (collection / document / get / set(merge) / update / delete / stream / list_documents, the Increment sentinel),
over the tables in migrations/. The code above it doesn't change: wilo.data.connect() hands out this client
instead of Firestore's when WILO_DB=postgres, or a Dual one when WILO_DB=dual.

Each doc is one row, its fields as JSONB in `data`, exactly the Firestore doc's shape. Paths map to tables
(locate()); a path with no table of its own goes in `documents`, keyed by its collection path.

    Client(url)     the database at url (DATABASE_URL); applies migrations/ on first use
    Dual(fs, pg)    reads from Firestore; every write goes to Firestore, then the doc is copied to Postgres
    backfill(...)   copy every Firestore doc into Postgres (python -m wilo.data pg-backfill)
"""

import base64
import copy
import secrets
import string
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / 'migrations'

USER_SUBS = ('workouts', 'days', 'events', 'todos', 'coach')  # users/{uid}/<sub>, a table each
TOP = ('users', 'chat_threads', 'chat_spend', 'chat_usage', 'chat_feedback', 'exercise_media')
THREAD_SUBS = {'turns': 'chat_turns', 'usage': 'chat_thread_usage'}  # chat_threads/{id}/<sub>
READ_BUDGET = 40_000  # Firestore's free tier is 50k reads a day for the whole app (#225); backfill stops above this


def NotFound(message):
    """The error Firestore raises on update() of a missing doc, so callers catch the same thing either way."""
    try:
        from google.api_core.exceptions import NotFound as error
    except ImportError:  # pragma: no cover - google-api-core comes with firebase-admin
        error = KeyError
    return error(message)


def locate(coll_path):
    """A collection path -> (table, {key column: value}) that selects that collection's rows."""
    parts = coll_path.split('/')
    if any(not p for p in parts) or len(parts) % 2 == 0:
        raise ValueError(f'not a collection path: {coll_path!r}')
    if len(parts) == 1 and parts[0] in TOP:
        return parts[0], {}
    if len(parts) == 3 and parts[0] == 'users' and parts[2] in USER_SUBS:
        return parts[2], {'uid': parts[1]}
    if len(parts) == 3 and parts[0] == 'chat_threads' and parts[2] in THREAD_SUBS:
        return THREAD_SUBS[parts[2]], {'chat_id': parts[1]}
    return 'documents', {'collection': coll_path}


def plain(value):
    """A Firestore value as JSON: timestamps as ISO strings (like the rest of the data), refs as their path,
    bytes as base64. Everything the app writes itself is already plain JSON."""
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, datetime):
        value = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return base64.b64encode(value).decode()
    if hasattr(value, 'path') and hasattr(value, 'id') and not isinstance(value, str):  # a DocumentReference
        return value.path
    if hasattr(value, 'latitude') and hasattr(value, 'longitude'):  # a GeoPoint
        return {'latitude': value.latitude, 'longitude': value.longitude}
    return value


def _is_increment(v):
    return type(v).__name__ == 'Increment' and hasattr(v, 'value')


def _resolve(old, new, deep):
    """new written over old: Increment adds to the stored number (0 when missing), as Firestore does; with deep
    (set with merge=True), nested maps merge too."""
    out = dict(old)
    for k, v in new.items():
        if _is_increment(v):
            base = old.get(k)
            out[k] = (base if isinstance(base, (int, float)) and not isinstance(base, bool) else 0) + v.value
        elif deep and isinstance(v, dict) and isinstance(old.get(k), dict):
            out[k] = _resolve(old[k], v, True)
        else:
            out[k] = plain(v)
    return out


def _auto_id():
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(20))


class Snapshot:
    def __init__(self, ref, data):
        self.reference, self.id, self.exists, self._data = ref, ref.id, data is not None, data

    def to_dict(self):
        return copy.deepcopy(self._data)


class DocumentRef:
    def __init__(self, client, coll_path, doc_id):
        if not doc_id or '/' in doc_id:
            raise ValueError(f'bad document id: {doc_id!r}')
        self.client, self.id = client, doc_id
        self.parent = CollectionRef(client, coll_path)
        self.path = f'{coll_path}/{doc_id}'

    def collection(self, name):
        return CollectionRef(self.client, f'{self.path}/{name}')

    def get(self):
        return Snapshot(self, self.client.read(self.parent.path, self.id))

    def set(self, document_data, merge=False):
        self.client.write(self.parent.path, self.id, document_data, merge=merge)

    def update(self, field_updates):
        self.client.update(self.parent.path, self.id, field_updates)

    def delete(self):
        self.client.delete(self.parent.path, self.id)


class CollectionRef:
    def __init__(self, client, path):
        locate(path)  # fails early on a bad path
        self.client, self.path, self.id = client, path, path.rsplit('/', 1)[-1]

    def document(self, document_id=None):
        return DocumentRef(self.client, self.path, document_id or _auto_id())

    def stream(self):
        return [Snapshot(DocumentRef(self.client, self.path, k), v) for k, v in self.client.rows(self.path)]

    def get(self):
        return self.stream()

    def list_documents(self):
        """Every doc id in the collection, also ids that only have subcollections (as Firestore's does)."""
        return [DocumentRef(self.client, self.path, k) for k in self.client.doc_ids(self.path)]


class Client:
    """Postgres behind the Firestore calls the app makes. One transaction per call."""

    def __init__(self, url, min_size=1, max_size=5):
        from psycopg_pool import ConnectionPool
        self.pool = ConnectionPool(url, min_size=min_size, max_size=max_size, open=True,
                                   check=ConnectionPool.check_connection, kwargs={'autocommit': False})
        with self.pool.connection() as conn:
            migrate(conn)

    def close(self):
        self.pool.close()

    def collection(self, name):
        return CollectionRef(self, name)

    # ---- SQL ----------------------------------------------------------------

    @staticmethod
    def _where(keys, doc_id=None):
        from psycopg import sql
        conds = [sql.SQL('{} = %s').format(sql.Identifier(k)) for k in keys]
        args = list(keys.values())
        if doc_id is not None:
            conds.append(sql.SQL('doc_id = %s'))
            args.append(doc_id)
        return (sql.SQL(' AND ').join(conds) if conds else sql.SQL('TRUE')), args

    @staticmethod
    def _jsonb(doc):
        from psycopg.types.json import Jsonb
        return Jsonb(plain(doc))

    def _upsert(self, conn, table, keys, doc_id, doc):
        from psycopg import sql
        cols = [*keys, 'doc_id']
        conn.execute(sql.SQL('INSERT INTO {t} ({cols}, data, updated_at) VALUES ({vals}, %s, now()) '
                             'ON CONFLICT ({cols}) DO UPDATE SET data = EXCLUDED.data, updated_at = now()').format(
            t=sql.Identifier(table), cols=sql.SQL(', ').join(map(sql.Identifier, cols)),
            vals=sql.SQL(', ').join(sql.Placeholder() * len(cols))), [*keys.values(), doc_id, self._jsonb(doc)])

    def _select(self, conn, table, keys, doc_id, lock=False):
        from psycopg import sql
        where, args = self._where(keys, doc_id)
        row = conn.execute(sql.SQL('SELECT data FROM {} WHERE {}' + (' FOR UPDATE' if lock else '')).format(
            sql.Identifier(table), where), args).fetchone()
        return row[0] if row else None

    def read(self, coll_path, doc_id):
        table, keys = locate(coll_path)
        with self.pool.connection() as conn:
            return self._select(conn, table, keys, doc_id)

    def write(self, coll_path, doc_id, doc, merge=False):
        table, keys = locate(coll_path)
        with self.pool.connection() as conn:
            if not merge and not any(_is_increment(v) for v in doc.values()):
                self._upsert(conn, table, keys, doc_id, doc)
                return
            # Read-modify-write under a row lock, so two writers (e.g. two chat requests adding their cost to
            # chat_spend with Increment) can't lose one another's change. The placeholder row only exists
            # inside this transaction.
            from psycopg import sql
            cols = [*keys, 'doc_id']
            conn.execute(sql.SQL("INSERT INTO {t} ({cols}, data) VALUES ({vals}, '{{}}') ON CONFLICT DO NOTHING").format(
                t=sql.Identifier(table), cols=sql.SQL(', ').join(map(sql.Identifier, cols)),
                vals=sql.SQL(', ').join(sql.Placeholder() * len(cols))), [*keys.values(), doc_id])
            old = self._select(conn, table, keys, doc_id, lock=True) if merge else {}
            self._upsert(conn, table, keys, doc_id, _resolve(old or {}, doc, deep=True))

    def update(self, coll_path, doc_id, fields):
        """Firestore's update(): the doc must exist; 'a.b' keys set a nested field; other values replace the field."""
        table, keys = locate(coll_path)
        with self.pool.connection() as conn:
            old = self._select(conn, table, keys, doc_id, lock=True)
            if old is None:
                raise NotFound(f'No document to update: {coll_path}/{doc_id}')
            new = copy.deepcopy(old)
            for path, v in fields.items():
                *parents, last = path.split('.')
                node = new
                for p in parents:
                    if not isinstance(node.get(p), dict):
                        node[p] = {}
                    node = node[p]
                node.update(_resolve(node, {last: v}, deep=False))
            self._upsert(conn, table, keys, doc_id, new)

    def delete(self, coll_path, doc_id):
        from psycopg import sql
        table, keys = locate(coll_path)
        where, args = self._where(keys, doc_id)
        with self.pool.connection() as conn:
            conn.execute(sql.SQL('DELETE FROM {} WHERE {}').format(sql.Identifier(table), where), args)

    def rows(self, coll_path):
        """(doc_id, data) for every doc in the collection, by doc id (Firestore's order)."""
        from psycopg import sql
        table, keys = locate(coll_path)
        where, args = self._where(keys)
        with self.pool.connection() as conn:
            return conn.execute(sql.SQL('SELECT doc_id, data FROM {} WHERE {} ORDER BY doc_id COLLATE "C"').format(
                sql.Identifier(table), where), args).fetchall()

    def doc_ids(self, coll_path):
        table, keys = locate(coll_path)
        from psycopg import sql
        where, args = self._where(keys)
        q = [sql.SQL('SELECT doc_id FROM {} WHERE {}').format(sql.Identifier(table), where)]
        if coll_path == 'users':
            q += [sql.SQL('SELECT uid FROM {}').format(sql.Identifier(t)) for t in USER_SUBS]
        if coll_path == 'chat_threads':
            q += [sql.SQL('SELECT chat_id FROM {}').format(sql.Identifier(t)) for t in THREAD_SUBS.values()]
        # Docs that only exist as the parent of a generic subcollection (e.g. users/{uid}/assigned).
        depth = coll_path.count('/') + 2
        q.append(sql.SQL("SELECT split_part(collection, '/', %s::int) FROM documents WHERE collection LIKE %s"))
        args = args + [depth, coll_path.replace('%', r'\%').replace('_', r'\_') + '/%/%']
        with self.pool.connection() as conn:
            rows = conn.execute(sql.SQL('SELECT id FROM ({}) ids (id) ORDER BY id COLLATE "C"').format(
                sql.SQL(' UNION ').join(q)), args).fetchall()
        return [r[0] for r in rows]

    def replace_collection(self, coll_path, docs):
        """Make the collection exactly docs ({doc_id: data}): upsert each, delete the rest. One transaction."""
        from psycopg import sql
        table, keys = locate(coll_path)
        where, args = self._where(keys)
        with self.pool.connection() as conn:
            for doc_id, data in docs.items():
                self._upsert(conn, table, keys, doc_id, data)
            conn.execute(sql.SQL('DELETE FROM {} WHERE {} AND NOT (doc_id = ANY(%s))').format(
                sql.Identifier(table), where), [*args, list(docs)])

    def truncate_all(self):
        """Tests only: empty every table."""
        with self.pool.connection() as conn:
            tables = [r[0] for r in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = current_schema() AND tablename <> 'schema_migrations'")]
            if tables:
                conn.execute('TRUNCATE ' + ', '.join(f'"{t}"' for t in tables))


def migrate(conn):
    """Apply each migrations/NNN_*.sql not applied yet, in order, once (an advisory lock keeps two servers
    starting together from both applying it)."""
    conn.execute('SELECT pg_advisory_xact_lock(241)')
    conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations '
                 '(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())')
    done = {r[0] for r in conn.execute('SELECT version FROM schema_migrations')}
    for f in sorted(MIGRATIONS.glob('*.sql')):
        if f.stem not in done:
            conn.execute(f.read_text())
            conn.execute('INSERT INTO schema_migrations (version) VALUES (%s)', [f.stem])
    conn.commit()


# ---- dual-write -------------------------------------------------------------
# During the cutover: Firestore stays the source of truth, Postgres follows. Each write goes to Firestore first,
# then the doc as Firestore now has it is copied to Postgres (one extra Firestore read per write, so merge and
# Increment come out exactly as Firestore computed them). A Postgres failure is logged, never raised: the app
# keeps working on Firestore, and pg-backfill catches Postgres up.

def _log(err, path):
    print(f'pg dual-write: {path}: {err!r}', flush=True)


class Dual:
    def __init__(self, fs, pg):
        self.fs, self.pg = fs, pg

    def collection(self, name):
        return DualCollection(self.fs.collection(name), self.pg.collection(name))

    def __getattr__(self, name):
        return getattr(self.fs, name)


class DualCollection:
    def __init__(self, fs, pg):
        self.fs, self.pg = fs, pg

    def document(self, document_id=None):
        document_id = document_id or _auto_id()
        return DualDoc(self.fs.document(document_id), self.pg.document(document_id))

    def __getattr__(self, name):  # stream, list_documents, get, id, ...: Firestore's
        return getattr(self.fs, name)


class DualDoc:
    def __init__(self, fs, pg):
        self.fs, self.pg = fs, pg

    def collection(self, name):
        return DualCollection(self.fs.collection(name), self.pg.collection(name))

    def _mirror(self):
        try:
            snap = self.fs.get()
            if snap.exists:
                self.pg.set(snap.to_dict())
            else:
                self.pg.delete()
        except Exception as err:  # never break the app over the copy
            _log(err, self.pg.path)

    def set(self, document_data, merge=False):
        self.fs.set(document_data, merge=merge)
        self._mirror()

    def update(self, field_updates):
        self.fs.update(field_updates)
        self._mirror()

    def delete(self):
        self.fs.delete()
        try:
            self.pg.delete()
        except Exception as err:
            _log(err, self.pg.path)

    def __getattr__(self, name):  # get, id, path, ...: Firestore's
        return getattr(self.fs, name)


# ---- backfill ---------------------------------------------------------------
# Firestore -> Postgres, every collection, each doc read once (one stream per collection). The structure is
# known, so subcollections are only looked for where they exist: under users/{uid} (whatever is there) and
# chat_threads/{id} (turns, usage). A dry run counts with aggregation queries (1 read per 1,000 docs), so it
# says how many reads the real copy will cost before spending them.

def _pattern(path):
    """users/abc/workouts -> users/*/workouts: the summary never lists uids."""
    parts = path.split('/')
    return '/'.join('*' if i % 2 else p for i, p in enumerate(parts))


def _collections(fs):
    """Every collection path to copy, and its doc count (aggregation query)."""
    out = []
    for coll in fs.collections():
        out.append(coll.id)
        if coll.id == 'users':
            for user in coll.list_documents():
                out += [f'users/{user.id}/{sub.id}' for sub in user.collections()]
        elif coll.id == 'chat_threads':
            for thread in coll.list_documents():
                out += [f'chat_threads/{thread.id}/{sub}' for sub in THREAD_SUBS]
    return out


def _count(fs, path):
    return int(_ref(fs, path).count().get()[0][0].value)


def _ref(fs, path):
    parts = path.split('/')
    ref = fs.collection(parts[0])
    for i in range(1, len(parts), 2):
        ref = ref.document(parts[i]).collection(parts[i + 1])
    return ref


def backfill(fs, pg, write, force=False):
    """Copy Firestore into Postgres. Dry run (counts only, no Postgres needed) unless write. Each collection is
    made exactly what Firestore has: new and changed docs upserted, docs gone from Firestore deleted."""
    paths = _collections(fs)
    counts = {p: _count(fs, p) for p in paths}
    total = sum(counts.values())
    summary = {}
    for p, n in counts.items():
        summary[_pattern(p)] = summary.get(_pattern(p), 0) + n
    out = {'ok': True, 'dryRun': not write, 'docs': total, 'readsToCopy': total, 'collections': summary}
    if not write:
        return out
    if total > READ_BUDGET and not force:
        return {**out, 'ok': False, 'errors': [f'{total} reads is over the {READ_BUDGET} budget '
                                               '(free tier: 50k a day for the whole app); pass --force to go anyway']}
    for p in paths:
        docs = {s.id: plain(s.to_dict()) for s in _ref(fs, p).stream()}
        pg.replace_collection(p, docs)
    return out
