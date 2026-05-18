"""SQLite persistence layer (async via aiosqlite).

Schema:
  students      : one row per Telegram user who completed registration.
  questions     : one row per inbound question (text or voice).

A single shared connection is opened at startup. SQLite serializes writes
internally, and aiogram dispatches handlers in tasks on a single event loop,
so a single connection with WAL is the simplest correct choice.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    user_id       INTEGER PRIMARY KEY,
    username      TEXT,
    full_name     TEXT NOT NULL,
    phone         TEXT NOT NULL,
    program       TEXT NOT NULL,
    region        TEXT NOT NULL,
    registered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS questions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('text', 'voice')),
    content         TEXT,
    voice_file_id   TEXT,
    created_at      TEXT NOT NULL,
    answered_at     TEXT,
    FOREIGN KEY (user_id) REFERENCES students(user_id)
);

CREATE INDEX IF NOT EXISTS idx_questions_user_id ON questions(user_id);
CREATE INDEX IF NOT EXISTS idx_questions_answered ON questions(answered_at);
"""


@dataclass(frozen=True)
class Student:
    user_id: int
    username: Optional[str]
    full_name: str
    phone: str
    program: str
    region: str
    registered_at: str


class Database:
    """Thin async wrapper over a single aiosqlite connection."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._conn: Optional[aiosqlite.Connection] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute("PRAGMA foreign_keys=ON;")
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Students
    # ------------------------------------------------------------------
    async def upsert_student(
        self,
        *,
        user_id: int,
        username: Optional[str],
        full_name: str,
        phone: str,
        program: str,
        region: str,
    ) -> Student:
        now = _utc_now_iso()
        # Preserve original registered_at on re-registration so the user's
        # "joined" timestamp is stable.
        await self._conn.execute(
            """
            INSERT INTO students
                (user_id, username, full_name, phone, program, region, registered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                full_name  = excluded.full_name,
                phone      = excluded.phone,
                program    = excluded.program,
                region     = excluded.region
            """,
            (user_id, username, full_name, phone, program, region, now),
        )
        await self._conn.commit()
        student = await self.get_student(user_id)
        assert student is not None
        return student

    async def get_student(self, user_id: int) -> Optional[Student]:
        async with self._conn.execute(
            "SELECT * FROM students WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        return _row_to_student(row) if row else None

    async def all_student_ids(self) -> list[int]:
        async with self._conn.execute(
            "SELECT user_id FROM students ORDER BY registered_at ASC"
        ) as cur:
            rows = await cur.fetchall()
        return [r["user_id"] for r in rows]

    async def all_students(self) -> list[Student]:
        async with self._conn.execute(
            "SELECT * FROM students ORDER BY registered_at ASC"
        ) as cur:
            rows = await cur.fetchall()
        return [_row_to_student(r) for r in rows]

    async def stats(self) -> dict:
        async with self._conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN program = ? THEN 1 ELSE 0 END) AS bakalavr,
                SUM(CASE WHEN program = ? THEN 1 ELSE 0 END) AS magistr
            FROM students
            """,
            ("Bakalavriat", "Magistratura"),
        ) as cur:
            srow = await cur.fetchone()
        async with self._conn.execute(
            """
            SELECT
                COUNT(*) AS q_total,
                SUM(CASE WHEN answered_at IS NULL THEN 1 ELSE 0 END) AS q_unanswered
            FROM questions
            """
        ) as cur:
            qrow = await cur.fetchone()
        return {
            "total": srow["total"] or 0,
            "bakalavr": srow["bakalavr"] or 0,
            "magistr": srow["magistr"] or 0,
            "q_total": qrow["q_total"] or 0,
            "q_unanswered": qrow["q_unanswered"] or 0,
        }

    async def total_students(self) -> int:
        async with self._conn.execute(
            "SELECT COUNT(*) AS n FROM students"
        ) as cur:
            row = await cur.fetchone()
        return int(row["n"] or 0)

    # ------------------------------------------------------------------
    # Questions
    # ------------------------------------------------------------------
    async def add_text_question(self, user_id: int, content: str) -> int:
        cur = await self._conn.execute(
            """
            INSERT INTO questions (user_id, kind, content, created_at)
            VALUES (?, 'text', ?, ?)
            """,
            (user_id, content, _utc_now_iso()),
        )
        await self._conn.commit()
        return cur.lastrowid

    async def add_voice_question(self, user_id: int, file_id: str) -> int:
        cur = await self._conn.execute(
            """
            INSERT INTO questions (user_id, kind, voice_file_id, created_at)
            VALUES (?, 'voice', ?, ?)
            """,
            (user_id, file_id, _utc_now_iso()),
        )
        await self._conn.commit()
        return cur.lastrowid

    async def mark_questions_answered(self, user_id: int) -> None:
        """Mark all unanswered questions from this user as answered.

        Admin replies are not pinned to a specific question, so the natural
        semantics are: any reply clears that user's open queue.
        """
        await self._conn.execute(
            """
            UPDATE questions
               SET answered_at = ?
             WHERE user_id = ?
               AND answered_at IS NULL
            """,
            (_utc_now_iso(), user_id),
        )
        await self._conn.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _row_to_student(row: aiosqlite.Row) -> Student:
    return Student(
        user_id=row["user_id"],
        username=row["username"],
        full_name=row["full_name"],
        phone=row["phone"],
        program=row["program"],
        region=row["region"],
        registered_at=row["registered_at"],
    )


def students_to_csv_rows(students: Iterable[Student]) -> list[list[str]]:
    header = ["full_name", "phone", "program", "region", "username", "registered_at"]
    out: list[list[str]] = [header]
    for s in students:
        out.append([
            s.full_name,
            s.phone,
            s.program,
            s.region,
            s.username or "",
            s.registered_at,
        ])
    return out
