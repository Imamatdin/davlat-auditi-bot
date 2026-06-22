"""SQLite persistence layer (async via aiosqlite).

Schema:
  students                : one row per Telegram user who completed registration.
  questions               : one row per inbound question (text or voice).
  question_notifications  : one row per (question, admin) pair, recording the
                            Telegram message_id of the admin's notification so
                            it can be edited when another admin answers.

A single shared connection is opened at startup. SQLite serializes writes
internally, and aiogram dispatches handlers in tasks on a single event loop,
so a single connection with WAL is the simplest correct choice.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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

-- One phone per registered student. Index variant is used (not column UNIQUE)
-- so the constraint can also retrofit onto an existing deployment if the
-- table predated this rule.
CREATE UNIQUE INDEX IF NOT EXISTS idx_students_phone_unique ON students(phone);

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

CREATE TABLE IF NOT EXISTS question_notifications (
    question_id   INTEGER NOT NULL,
    admin_id      INTEGER NOT NULL,
    message_id    INTEGER NOT NULL,
    original_text TEXT NOT NULL,
    PRIMARY KEY (question_id, admin_id),
    FOREIGN KEY (question_id) REFERENCES questions(id)
);

CREATE INDEX IF NOT EXISTS idx_qnotif_question ON question_notifications(question_id);

-- Canned answers an admin can reuse. keyword is the lookup handle (normalized
-- to lowercase before storage) and is unique. created_at is preserved across
-- re-adds of the same keyword (see add_faq).
CREATE TABLE IF NOT EXISTS faq (
    keyword     TEXT PRIMARY KEY,
    answer_text TEXT NOT NULL,
    created_by  INTEGER NOT NULL,
    created_at  TEXT NOT NULL
);
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


@dataclass(frozen=True)
class Question:
    id: int
    user_id: int
    kind: str
    content: Optional[str]
    voice_file_id: Optional[str]
    created_at: str
    answered_at: Optional[str]


@dataclass(frozen=True)
class Notification:
    question_id: int
    admin_id: int
    message_id: int
    original_text: str


@dataclass(frozen=True)
class QueueItem:
    """A single unanswered question joined with its author, for /queue."""
    id: int
    kind: str
    content: Optional[str]
    created_at: str
    full_name: str
    program: str


@dataclass(frozen=True)
class Faq:
    keyword: str
    answer_text: str
    created_by: int
    created_at: str


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

    async def get_student_by_phone(self, phone: str) -> Optional[Student]:
        async with self._conn.execute(
            "SELECT * FROM students WHERE phone = ?", (phone,)
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
        q_total = qrow["q_total"] or 0
        q_unanswered = qrow["q_unanswered"] or 0
        return {
            "total": srow["total"] or 0,
            "bakalavr": srow["bakalavr"] or 0,
            "magistr": srow["magistr"] or 0,
            "q_total": q_total,
            "q_unanswered": q_unanswered,
            "q_answered": q_total - q_unanswered,
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

    async def count_recent_questions(self, user_id: int, hours: int) -> int:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=hours)
        ).replace(microsecond=0).isoformat()
        async with self._conn.execute(
            """
            SELECT COUNT(*) AS n
              FROM questions
             WHERE user_id = ?
               AND created_at > ?
            """,
            (user_id, cutoff),
        ) as cur:
            row = await cur.fetchone()
        return int(row["n"] or 0)

    async def get_question(self, question_id: int) -> Optional[Question]:
        async with self._conn.execute(
            "SELECT * FROM questions WHERE id = ?", (question_id,)
        ) as cur:
            row = await cur.fetchone()
        return _row_to_question(row) if row else None

    async def mark_question_answered(self, question_id: int) -> None:
        await self._conn.execute(
            """
            UPDATE questions
               SET answered_at = ?
             WHERE id = ?
               AND answered_at IS NULL
            """,
            (_utc_now_iso(), question_id),
        )
        await self._conn.commit()

    async def count_open_questions(self) -> int:
        async with self._conn.execute(
            "SELECT COUNT(*) AS n FROM questions WHERE answered_at IS NULL"
        ) as cur:
            row = await cur.fetchone()
        return int(row["n"] or 0)

    async def get_open_questions(self, *, limit: int, offset: int) -> list["QueueItem"]:
        """Unanswered questions, oldest first, joined with author name+program."""
        async with self._conn.execute(
            """
            SELECT q.id, q.kind, q.content, q.created_at,
                   s.full_name, s.program
              FROM questions q
              JOIN students s ON s.user_id = q.user_id
             WHERE q.answered_at IS NULL
             ORDER BY q.created_at ASC, q.id ASC
             LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ) as cur:
            rows = await cur.fetchall()
        return [
            QueueItem(
                id=r["id"],
                kind=r["kind"],
                content=r["content"],
                created_at=r["created_at"],
                full_name=r["full_name"],
                program=r["program"],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    async def add_notification(
        self,
        *,
        question_id: int,
        admin_id: int,
        message_id: int,
        original_text: str,
    ) -> None:
        await self._conn.execute(
            """
            INSERT OR REPLACE INTO question_notifications
                (question_id, admin_id, message_id, original_text)
            VALUES (?, ?, ?, ?)
            """,
            (question_id, admin_id, message_id, original_text),
        )
        await self._conn.commit()

    async def get_notifications(self, question_id: int) -> list[Notification]:
        async with self._conn.execute(
            """
            SELECT question_id, admin_id, message_id, original_text
              FROM question_notifications
             WHERE question_id = ?
            """,
            (question_id,),
        ) as cur:
            rows = await cur.fetchall()
        return [
            Notification(
                question_id=r["question_id"],
                admin_id=r["admin_id"],
                message_id=r["message_id"],
                original_text=r["original_text"],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # FAQ (canned answers)
    # ------------------------------------------------------------------
    async def add_faq(self, *, keyword: str, answer_text: str, created_by: int) -> None:
        # Re-adding an existing keyword updates the answer and editor but keeps
        # the original created_at (DO UPDATE leaves created_at untouched).
        await self._conn.execute(
            """
            INSERT INTO faq (keyword, answer_text, created_by, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(keyword) DO UPDATE SET
                answer_text = excluded.answer_text,
                created_by  = excluded.created_by
            """,
            (keyword, answer_text, created_by, _utc_now_iso()),
        )
        await self._conn.commit()

    async def get_faq(self, keyword: str) -> Optional[Faq]:
        async with self._conn.execute(
            "SELECT keyword, answer_text, created_by, created_at FROM faq WHERE keyword = ?",
            (keyword,),
        ) as cur:
            row = await cur.fetchone()
        return _row_to_faq(row) if row else None

    async def all_faqs(self) -> list[Faq]:
        async with self._conn.execute(
            "SELECT keyword, answer_text, created_by, created_at FROM faq ORDER BY keyword ASC"
        ) as cur:
            rows = await cur.fetchall()
        return [_row_to_faq(r) for r in rows]

    async def delete_faq(self, keyword: str) -> bool:
        cur = await self._conn.execute("DELETE FROM faq WHERE keyword = ?", (keyword,))
        await self._conn.commit()
        return cur.rowcount > 0


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


def _row_to_question(row: aiosqlite.Row) -> Question:
    return Question(
        id=row["id"],
        user_id=row["user_id"],
        kind=row["kind"],
        content=row["content"],
        voice_file_id=row["voice_file_id"],
        created_at=row["created_at"],
        answered_at=row["answered_at"],
    )


def _row_to_faq(row: aiosqlite.Row) -> Faq:
    return Faq(
        keyword=row["keyword"],
        answer_text=row["answer_text"],
        created_by=row["created_by"],
        created_at=row["created_at"],
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
