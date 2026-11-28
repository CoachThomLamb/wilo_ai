-- WILO on Postgres (#241). One table per Firestore collection. Each doc's fields stay as JSONB in `data`,
-- the same shape as the Firestore doc (schema/workout.schema.json for workouts), so wilo/data.py doesn't
-- change. The columns pulled out of `data` are generated, for queries and indexes only.
-- Path map (wilo/pg.py): users/{uid} -> users; users/{uid}/<sub>/{id} -> <sub> (workouts, days, events,
-- todos, coach); chat_threads/{id}/turns|usage/{id} -> chat_turns | chat_thread_usage; any other path ->
-- documents (collection path + id), e.g. oauth_* and the old users/{uid}/assigned|completed backups (#200).

CREATE TABLE IF NOT EXISTS users (
    doc_id     text PRIMARY KEY,                 -- the Firebase uid
    data       jsonb NOT NULL,                   -- email, name, photo, lastSignIn, createdAt (fe/auth.js)
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- users/{uid}/workouts: one doc per workout from plan to done (#126).
CREATE TABLE IF NOT EXISTS workouts (
    uid          text NOT NULL,
    doc_id       text NOT NULL,
    data         jsonb NOT NULL,
    updated_at   timestamptz NOT NULL DEFAULT now(),
    status       text GENERATED ALWAYS AS (data->>'status') STORED,
    assigned_for text GENERATED ALWAYS AS (data->>'assignedFor') STORED,
    PRIMARY KEY (uid, doc_id)
);
CREATE INDEX IF NOT EXISTS workouts_uid_assigned_for ON workouts (uid, assigned_for);
CREATE INDEX IF NOT EXISTS workouts_uid_status ON workouts (uid, status);

-- users/{uid}/days (the Day page, #156; doc id = YYYY-MM-DD), events (#168), todos (#64),
-- coach (doc ids `profile` #48 and `records` #236).
CREATE TABLE IF NOT EXISTS days (
    uid text NOT NULL, doc_id text NOT NULL, data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (uid, doc_id)
);
CREATE TABLE IF NOT EXISTS events (
    uid text NOT NULL, doc_id text NOT NULL, data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
    date text GENERATED ALWAYS AS (data->>'date') STORED,
    PRIMARY KEY (uid, doc_id)
);
CREATE INDEX IF NOT EXISTS events_uid_date ON events (uid, date);
CREATE TABLE IF NOT EXISTS todos (
    uid text NOT NULL, doc_id text NOT NULL, data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (uid, doc_id)
);
CREATE TABLE IF NOT EXISTS coach (
    uid text NOT NULL, doc_id text NOT NULL, data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (uid, doc_id)
);

-- The coach chat (wilo/chat.py): threads, their turns and per-request usage, spend, daily quota, ratings.
CREATE TABLE IF NOT EXISTS chat_threads (
    doc_id text PRIMARY KEY, data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
    uid text GENERATED ALWAYS AS (data->>'uid') STORED
);
CREATE INDEX IF NOT EXISTS chat_threads_uid ON chat_threads (uid);
CREATE TABLE IF NOT EXISTS chat_turns (
    chat_id text NOT NULL, doc_id text NOT NULL, data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (chat_id, doc_id)
);
CREATE TABLE IF NOT EXISTS chat_thread_usage (
    chat_id text NOT NULL, doc_id text NOT NULL, data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (chat_id, doc_id)
);
CREATE TABLE IF NOT EXISTS chat_spend (      -- doc id = uid
    doc_id text PRIMARY KEY, data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS chat_usage (      -- doc id = {uid}_{YYYY-MM-DD}
    doc_id text PRIMARY KEY, data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS chat_feedback (   -- doc id = chat id
    doc_id text PRIMARY KEY, data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now()
);

-- Exercise demo media (wilo/media.py), doc id = exercise slug.
CREATE TABLE IF NOT EXISTS exercise_media (
    doc_id text PRIMARY KEY, data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now()
);

-- Everything else, by full collection path: oauth_* (wilo/auth.py), users/{uid}/assigned|completed (#200), ...
CREATE TABLE IF NOT EXISTS documents (
    collection text NOT NULL, doc_id text NOT NULL, data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (collection, doc_id)
);
