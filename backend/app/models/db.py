"""SQLite persistence (stdlib sqlite3): research jobs, sources/evidence, reports, follow-ups, history."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from app.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS research (
    id            TEXT PRIMARY KEY,
    topic         TEXT NOT NULL,
    mode          TEXT NOT NULL,
    status        TEXT NOT NULL,
    stage         TEXT NOT NULL DEFAULT '',
    progress      INTEGER NOT NULL DEFAULT 0,
    objective     TEXT NOT NULL DEFAULT '',
    queries_json  TEXT NOT NULL DEFAULT '[]',
    sources_json  TEXT NOT NULL DEFAULT '[]',
    warnings_json TEXT NOT NULL DEFAULT '[]',
    report_json   TEXT,
    error_json    TEXT,
    saved         INTEGER NOT NULL DEFAULT 0,
    client_id     TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    completed_at  TEXT
);
CREATE TABLE IF NOT EXISTS followups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    research_id TEXT NOT NULL REFERENCES research(id) ON DELETE CASCADE,
    answer_json TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_research_created ON research(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_followups_research ON followups(research_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    path = get_settings().db_file
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def init_db() -> None:
    with _conn() as c:
        c.execute("PRAGMA journal_mode = WAL")
        c.executescript(SCHEMA)
        # Migration for databases created before history was scoped per browser.
        cols = {r["name"] for r in c.execute("PRAGMA table_info(research)")}
        if "client_id" not in cols:
            c.execute("ALTER TABLE research ADD COLUMN client_id TEXT")
        c.execute("CREATE INDEX IF NOT EXISTS idx_research_client ON research(client_id, created_at DESC)")


def mark_interrupted() -> int:
    """Jobs that were running when the server stopped can never finish: fail them clearly."""
    err = json.dumps({"code": "INTERRUPTED", "message": "The server restarted while this research was running. Please retry.", "retryable": True})
    with _conn() as c:
        cur = c.execute(
            "UPDATE research SET status='failed', stage='Interrupted', error_json=?, updated_at=? WHERE status IN ('queued','running')",
            (err, _now()),
        )
        return cur.rowcount


def create_research(topic: str, mode: str, client_id: str | None = None) -> str:
    rid = uuid.uuid4().hex[:16]
    now = _now()
    with _conn() as c:
        c.execute(
            "INSERT INTO research (id, topic, mode, status, stage, progress, client_id, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (rid, topic, mode, "queued", "Queued", 0, client_id, now, now),
        )
    return rid


def get_research(rid: str) -> dict[str, Any] | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM research WHERE id=?", (rid,)).fetchone()
    return dict(row) if row else None


def _update(rid: str, **fields: Any) -> None:
    fields["updated_at"] = _now()
    cols = ", ".join(f"{k}=?" for k in fields)
    with _conn() as c:
        c.execute(f"UPDATE research SET {cols} WHERE id=?", (*fields.values(), rid))


def update_progress(rid: str, stage: str, progress: int, status: str = "running") -> None:
    _update(rid, status=status, stage=stage, progress=progress)


def save_plan(rid: str, objective: str, queries: list[str]) -> None:
    _update(rid, objective=objective, queries_json=json.dumps(queries))


def save_sources(rid: str, sources: list[dict], warnings: list[str]) -> None:
    _update(rid, sources_json=json.dumps(sources), warnings_json=json.dumps(warnings))


def complete(rid: str, report: dict, warnings: list[str]) -> None:
    _update(
        rid, status="completed", stage="Done", progress=100, report_json=json.dumps(report),
        warnings_json=json.dumps(warnings), error_json=None, completed_at=_now(),
    )


def fail(rid: str, code: str, message: str, retryable: bool) -> None:
    _update(
        rid, status="failed", stage="Failed",
        error_json=json.dumps({"code": code, "message": message, "retryable": retryable}),
    )


def reset_for_retry(rid: str) -> None:
    _update(
        rid, status="queued", stage="Queued", progress=0, objective="", queries_json="[]",
        sources_json="[]", warnings_json="[]", report_json=None, error_json=None, completed_at=None,
    )


def set_saved(rid: str, saved: bool) -> bool:
    with _conn() as c:
        cur = c.execute("UPDATE research SET saved=?, updated_at=? WHERE id=?", (int(saved), _now(), rid))
        return cur.rowcount > 0


def delete_research(rid: str) -> bool:
    with _conn() as c:
        return c.execute("DELETE FROM research WHERE id=?", (rid,)).rowcount > 0


def list_history(limit: int, offset: int, saved_only: bool, client_id: str | None) -> list[dict[str, Any]]:
    """History for ONE browser (client_id). Rows without an owner (legacy) are never listed to anyone.

    title / sources_count are computed in SQL so the (large) report and evidence JSON is not parsed in Python.
    """
    if not client_id:
        return []
    where = "WHERE client_id = ?" + (" AND saved = 1" if saved_only else "")
    with _conn() as c:
        rows = c.execute(
            "SELECT id, topic, mode, status, saved, created_at, completed_at, "
            "COALESCE(json_extract(report_json, '$.title'), '') AS title, "
            "COALESCE(json_array_length(sources_json), 0) AS sources_count "
            f"FROM research {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (client_id, limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]


def add_followup(rid: str, answer: dict) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO followups (research_id, answer_json, created_at) VALUES (?,?,?)",
            (rid, json.dumps(answer, default=str), _now()),
        )


def list_followups(rid: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT answer_json FROM followups WHERE research_id=? ORDER BY id", (rid,)).fetchall()
    return [json.loads(r["answer_json"]) for r in rows]
