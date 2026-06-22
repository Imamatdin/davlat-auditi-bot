"""Daily CSV backup of the database, delivered to admins over Telegram.

Runs as an asyncio task inside the bot's event loop (no external scheduler).
Once a day at BACKUP_HOUR_UTC it exports the students and questions tables to
CSV, reusing the same builder and Excel-injection guard as /export, and sends
both files to every admin with a short summary caption. A blocked admin or a
network blip is logged and never crashes the loop.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import BufferedInputFile

from . import texts
from .config import ADMIN_IDS
from .db import Database, questions_to_csv_rows, students_to_csv_rows
from .utils import build_students_csv

log = logging.getLogger(__name__)

# The Railway container runs on UTC. 03:00 UTC is 08:00 in Uzbekistan (UTC+5,
# no DST), i.e. the admins receive the backup first thing in the morning.
BACKUP_HOUR_UTC = 3


def _seconds_until(hour: int, now: datetime) -> float:
    """Seconds from `now` until the next occurrence of `hour`:00 (same tz)."""
    nxt = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if nxt <= now:
        nxt += timedelta(days=1)
    return (nxt - now).total_seconds()


async def build_backup_files(db: Database) -> tuple[bytes, bytes, dict]:
    """Build (students_csv, questions_csv, stats) from the current DB state."""
    students = await db.all_students()
    questions = await db.all_questions()
    students_csv = build_students_csv(students_to_csv_rows(students))
    questions_csv = build_students_csv(questions_to_csv_rows(questions))
    stats = await db.stats()
    return students_csv, questions_csv, stats


async def run_backup_once(bot: Bot, db: Database, *, date_str: str) -> None:
    """Build both CSVs and send them to every admin. Never raises per-admin."""
    students_csv, questions_csv, stats = await build_backup_files(db)
    caption = texts.ADMIN_BACKUP_CAPTION.format(
        date=date_str,
        total=stats["total"],
        q_unanswered=stats["q_unanswered"],
    )
    students_doc = BufferedInputFile(students_csv, filename=f"talabalar_{date_str}.csv")
    questions_doc = BufferedInputFile(questions_csv, filename=f"savollar_{date_str}.csv")
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_document(admin_id, students_doc, caption=caption)
            await bot.send_document(admin_id, questions_doc)
        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            log.warning("Backup send to admin %s failed: %s", admin_id, exc)
        except Exception:  # pragma: no cover (defensive)
            log.exception("Unexpected error sending backup to admin %s", admin_id)


async def backup_scheduler(bot: Bot, db: Database) -> None:
    """Sleep until the next BACKUP_HOUR_UTC, send the backup, repeat daily."""
    log.info("Backup scheduler started (daily at %02d:00 UTC).", BACKUP_HOUR_UTC)
    while True:
        await asyncio.sleep(_seconds_until(BACKUP_HOUR_UTC, datetime.now(timezone.utc)))
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            await run_backup_once(bot, db, date_str=date_str)
            log.info("Daily backup sent for %s.", date_str)
        except Exception:  # pragma: no cover (defensive)
            log.exception("Daily backup failed for %s.", date_str)
        # Move off the trigger minute so the next _seconds_until lands tomorrow.
        await asyncio.sleep(61)
