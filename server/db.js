const Database = require('better-sqlite3');
const path = require('path');

const db = new Database(path.join(__dirname, 'wilo.db'));

db.exec(`
  CREATE TABLE IF NOT EXISTS microcycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_of TEXT NOT NULL UNIQUE,
    data TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    session_name TEXT,
    finished_at TEXT NOT NULL,
    data TEXT NOT NULL
  );
`);

module.exports = db;
