"""SQLite repository: immutable networks, versioned scenarios, audited ingestion."""

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .engine import digest


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, path: str):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_lock = threading.Lock()
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS networks(id TEXT PRIMARY KEY, body TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS scenarios(id TEXT NOT NULL, version INTEGER NOT NULL,
                    body TEXT NOT NULL, PRIMARY KEY(id, version));
                CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
                    body TEXT NOT NULL, request_hash TEXT NOT NULL, idempotency_key TEXT UNIQUE);
                CREATE TABLE IF NOT EXISTS ingestions(id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
                    filename TEXT NOT NULL, report TEXT NOT NULL, raw TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS mutations(key TEXT PRIMARY KEY, request_hash TEXT NOT NULL,
                    response TEXT NOT NULL);
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connection(self, readonly=False):
        uri = self.path.as_uri() + "?mode=ro" if readonly else str(self.path)
        db = sqlite3.connect(uri, uri=readonly, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            if readonly:
                db.execute("PRAGMA query_only=ON")
            yield db
            if not readonly:
                db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def network(self, identifier: str):
        with self.connection(True) as db:
            row = db.execute("SELECT body FROM networks WHERE id=?", (identifier,)).fetchone()
            return json.loads(row[0]) if row else None

    def put_network(self, body):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT hash FROM networks WHERE id=?", (body["id"],)).fetchone()
            if row and row[0] != digest(body):
                raise Conflict("Network ID exists with different data; import using a new ID")
            db.execute(
                "INSERT OR IGNORE INTO networks VALUES(?,?,?)", (body["id"], json.dumps(body), digest(body))
            )

    def list_networks(self):
        with self.connection(True) as db:
            return [dict(r) for r in db.execute("SELECT id, hash FROM networks ORDER BY id")]

    def save_scenario(self, body, key=None, request_hash=None):
        request_hash = request_hash or digest(body)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if key:
                old = db.execute("SELECT * FROM mutations WHERE key=?", (key,)).fetchone()
                if old:
                    if old["request_hash"] != request_hash:
                        raise Conflict("Idempotency key was used with different content")
                    return json.loads(old["response"])
            version = db.execute(
                "SELECT COALESCE(MAX(version),0)+1 FROM scenarios WHERE id=?", (body["id"],)
            ).fetchone()[0]
            body = {**body, "version": version}
            db.execute("INSERT INTO scenarios VALUES(?,?,?)", (body["id"], version, json.dumps(body)))
            if key:
                db.execute("INSERT INTO mutations VALUES(?,?,?)", (key, request_hash, json.dumps(body)))
            return body

    def scenarios(self, identifier=None):
        with self.connection(True) as db:
            if identifier:
                rows = db.execute(
                    "SELECT body FROM scenarios WHERE id=? ORDER BY version DESC", (identifier,)
                )
            else:
                rows = db.execute(
                    "SELECT body FROM scenarios s WHERE version=(SELECT MAX(version) FROM scenarios t WHERE t.id=s.id) ORDER BY id"
                )
            return [json.loads(r[0]) for r in rows]

    def existing_run(self, key, request_hash):
        if not key:
            return None
        with self.connection(True) as db:
            row = db.execute("SELECT * FROM runs WHERE idempotency_key=?", (key,)).fetchone()
            if row:
                if row["request_hash"] != request_hash:
                    raise Conflict("Idempotency key was used with a different run request")
                return {"id": row["id"], "created_at": row["created_at"], **json.loads(row["body"])}
        return None

    def save_run(self, body, key, request_hash):
        identifier, stamp = str(uuid4()), datetime.now(timezone.utc).isoformat()
        with self.connection() as db:
            db.execute(
                "INSERT INTO runs VALUES(?,?,?,?,?)", (identifier, stamp, json.dumps(body), request_hash, key)
            )
        return {"id": identifier, "created_at": stamp, **body}

    def run(self, identifier):
        with self.connection(True) as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (identifier,)).fetchone()
            return (
                {"id": row["id"], "created_at": row["created_at"], **json.loads(row["body"])} if row else None
            )

    def runs(self, limit, offset):
        with self.connection(True) as db:
            total = db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            rows = db.execute(
                "SELECT id, created_at, json_extract(body,'$.scenario.scenario.name') AS name FROM runs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            return dict(items=[dict(r) for r in rows], total=total, limit=limit, offset=offset)

    def ingestion(self, raw, filename, report):
        identifier = str(uuid4())
        with self.connection() as db:
            db.execute(
                "INSERT INTO ingestions VALUES(?,?,?,?,?)",
                (
                    identifier,
                    datetime.now(timezone.utc).isoformat(),
                    filename,
                    json.dumps(report),
                    json.dumps(raw),
                ),
            )
        return identifier

    def ingestions(self, limit, offset):
        with self.connection(True) as db:
            total = db.execute("SELECT COUNT(*) FROM ingestions").fetchone()[0]
            rows = db.execute(
                "SELECT id, created_at, filename, report FROM ingestions ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            return dict(
                items=[{**dict(r), "report": json.loads(r["report"])} for r in rows],
                total=total,
                limit=limit,
                offset=offset,
            )
