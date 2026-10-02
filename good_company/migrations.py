"""Versioned additive migration baseline. No authority or receipt rewrites."""
from contextlib import closing
import sqlite3
import uuid
from pathlib import Path

VERSION = 2
SCHEMA = """

        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS source_precedence(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS document_versions(
          source TEXT NOT NULL, version TEXT NOT NULL, metadata TEXT NOT NULL,
          payload TEXT NOT NULL, audience TEXT NOT NULL, PRIMARY KEY(source,version));
        CREATE TABLE IF NOT EXISTS retired_sources(source TEXT PRIMARY KEY, authority TEXT NOT NULL, retired_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS contact_preferences(address TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS communication_claims(
          kind TEXT NOT NULL, notice_id TEXT NOT NULL, address TEXT NOT NULL, at TEXT NOT NULL,
          PRIMARY KEY(kind,notice_id,address));
        CREATE TABLE IF NOT EXISTS contact_consent(
          address TEXT PRIMARY KEY, enabled INTEGER NOT NULL, authority TEXT NOT NULL, changed_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(
          id TEXT PRIMARY KEY, calendar TEXT NOT NULL, start TEXT NOT NULL,
          end TEXT NOT NULL, revision TEXT NOT NULL, payload TEXT NOT NULL,
          checked_at TEXT NOT NULL, cancelled INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS calendar_sync(
          calendar TEXT PRIMARY KEY, checked_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reminders(
          id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES events(id),
          revision TEXT NOT NULL, kind TEXT NOT NULL, due TEXT NOT NULL,
          status TEXT NOT NULL, message TEXT NOT NULL, approval TEXT,
          claimed_at TEXT, receipt TEXT, created_at TEXT NOT NULL,
          UNIQUE(event_id, revision, kind));
        CREATE TABLE IF NOT EXISTS audit(
          id INTEGER PRIMARY KEY, at TEXT NOT NULL, action TEXT NOT NULL,
          object_id TEXT NOT NULL, detail TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS dress_rules(
          id TEXT PRIMARY KEY, source TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge USING fts5(
          source UNINDEXED, title, section, content, updated UNINDEXED,
          audience UNINDEXED, tokenize='porter unicode61');
        
        CREATE TABLE IF NOT EXISTS volunteers(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS assignments(
          id TEXT PRIMARY KEY, task_id TEXT NOT NULL, volunteer_id TEXT NOT NULL,
          status TEXT NOT NULL, policy_hash TEXT NOT NULL,
          UNIQUE(task_id, volunteer_id));
        CREATE TABLE IF NOT EXISTS task_notices(
          id TEXT PRIMARY KEY, assignment_id TEXT NOT NULL, kind TEXT NOT NULL,
          due TEXT NOT NULL, status TEXT NOT NULL, message TEXT NOT NULL, receipt TEXT,
          UNIQUE(assignment_id, kind));
        CREATE TABLE IF NOT EXISTS corrections(
          id TEXT PRIMARY KEY, kind TEXT NOT NULL, original_id TEXT NOT NULL,
          revision TEXT NOT NULL, policy_hash TEXT NOT NULL, message TEXT NOT NULL,
          status TEXT NOT NULL, created_at TEXT NOT NULL, receipt TEXT, authority TEXT NOT NULL,
          UNIQUE(kind,original_id,revision));
        CREATE TABLE IF NOT EXISTS module_policies(
          module TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS module_records(
          module TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL,
          payload TEXT NOT NULL, status TEXT NOT NULL, expires_at TEXT NOT NULL,
          PRIMARY KEY(module,id));
        CREATE TABLE IF NOT EXISTS module_notices(
          id TEXT PRIMARY KEY, module TEXT NOT NULL, record_id TEXT NOT NULL,
          revision INTEGER NOT NULL, policy_hash TEXT NOT NULL,
          due TEXT NOT NULL, status TEXT NOT NULL, message TEXT NOT NULL, receipt TEXT);
"""


def migrate(db, path, schema=SCHEMA):
    db.execute('PRAGMA foreign_keys=ON')
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version > VERSION:
        raise ValueError('Database schema is newer than this application; use the matching release.')
    if version == VERSION:
        return
    existing = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if existing:
        # Keep a consistent private copy before any DDL. The full offline runtime
        # backup remains necessary for external install identity and credentials.
        backup = Path(str(path) + f'.pre-v{VERSION}.' + uuid.uuid4().hex + '.sqlite')
        fd = backup.open('xb'); fd.close(); backup.chmod(0o600)
        with closing(sqlite3.connect(backup)) as copy:
            db.backup(copy)
            if copy.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Pre-migration snapshot failed integrity verification.')
    try:
        db.execute('BEGIN IMMEDIATE')
        locked_version = db.execute('PRAGMA user_version').fetchone()[0]
        if locked_version > VERSION:
            raise ValueError('Database schema advanced beyond this application.')
        if locked_version == VERSION:
            db.rollback(); return
        # executescript implicitly commits, so execute individual complete SQL
        # statements to keep DDL and version advancement in one transaction.
        pending = ''
        for line in schema.splitlines(keepends=True):
            pending += line
            if sqlite3.complete_statement(pending):
                db.execute(pending); pending = ''
        if pending.strip():
            raise ValueError('Incomplete migration statement.')
        db.execute(f'PRAGMA user_version={VERSION}')
        db.commit()
    except Exception:
        db.rollback()
        raise
