"""Bot entrypoint.

Runs the aiogram dispatcher alongside a tiny aiohttp healthcheck server in
the same asyncio loop. Railway pings the healthcheck path, keeping the
service from being put to sleep.
"""
from __future__ import annotations

import asyncio
import hmac
import logging
import os
import signal
import sqlite3
from contextlib import suppress
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from . import config
from .db import Database
from .handlers import admin, questions, registration, start


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # aiogram is chatty at INFO. Keep its event-loop noise at WARNING.
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Middleware: inject the shared Database into every handler call
# ---------------------------------------------------------------------------

class DbInjector:
    """Aiogram middleware that adds `db` to every handler's kwargs."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def __call__(self, handler, event, data: dict[str, Any]):
        data["db"] = self._db
        return await handler(event, data)


# ---------------------------------------------------------------------------
# Healthcheck server
# ---------------------------------------------------------------------------

async def _healthcheck(_request: web.Request) -> web.Response:
    return web.Response(text="ok")


def _make_restore_handler(db: Database, db_path: str, restore_token: str):
    """One-off DB restore endpoint (disabled unless RESTORE_TOKEN is set).

    PUT/POST the raw bytes of a SQLite file. It is validated (magic header +
    integrity_check + students/questions tables), atomically swapped onto the
    volume at db_path, and the process then exits non-zero so Railway restarts
    it onto the restored DB. Auth is a constant-time token compare over HTTPS.
    """
    log = logging.getLogger(__name__)

    async def _restore(request: web.Request) -> web.Response:
        if not restore_token:
            return web.Response(status=404, text="not found\n")
        supplied = request.query.get("token") or request.headers.get("X-Restore-Token", "")
        if not (supplied and hmac.compare_digest(supplied, restore_token)):
            return web.Response(status=403, text="forbidden\n")

        body = await request.read()
        if not body.startswith(b"SQLite format 3\x00"):
            return web.Response(status=400, text="not a sqlite database\n")

        tmp = db_path + ".upload"
        try:
            with open(tmp, "wb") as f:
                f.write(body)
            con = sqlite3.connect(tmp)
            integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
            n_students = con.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            n_questions = con.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
            con.execute("PRAGMA journal_mode=DELETE")  # collapse to a single self-contained file
            con.commit()
            con.close()
        except Exception as exc:
            with suppress(FileNotFoundError):
                os.remove(tmp)
            return web.Response(status=400, text=f"invalid db: {exc}\n")
        if integrity != "ok":
            with suppress(FileNotFoundError):
                os.remove(tmp)
            return web.Response(status=400, text=f"integrity_check: {integrity}\n")

        await db.close()
        os.replace(tmp, db_path)
        for sfx in ("-wal", "-shm", ".upload-wal", ".upload-shm"):
            with suppress(FileNotFoundError):
                os.remove(db_path + sfx)
        log.warning(
            "DB RESTORED via /restore (students=%s questions=%s). Exiting to restart.",
            n_students, n_questions,
        )
        # Flush the response first, then exit non-zero so Railway (ON_FAILURE)
        # restarts the process, which reopens the freshly swapped DB.
        asyncio.get_running_loop().call_later(0.5, lambda: os._exit(42))
        return web.Response(
            text=f"restored: students={n_students} questions={n_questions}; restarting\n"
        )

    return _restore


async def _start_health_server(
    port: int, *, db: Database, db_path: str, restore_token: str
) -> web.AppRunner:
    log = logging.getLogger(__name__)
    # 64 MiB cap so a DB upload is accepted (default aiohttp limit is 1 MiB).
    app = web.Application(client_max_size=64 * 1024 * 1024)
    app.router.add_get("/", _healthcheck)
    app.router.add_get("/healthz", _healthcheck)
    restore = _make_restore_handler(db, db_path, restore_token)
    app.router.add_route("PUT", "/restore", restore)
    app.router.add_route("POST", "/restore", restore)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    log.info("Healthcheck listening on 0.0.0.0:%s", port)
    if restore_token:
        log.warning("/restore endpoint ENABLED (RESTORE_TOKEN set). Unset it after restoring.")
    return runner


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    _setup_logging()
    log = logging.getLogger(__name__)

    db = Database(config.DB_PATH)
    await db.connect()
    log.info("Database ready at %s", config.DB_PATH)

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    injector = DbInjector(db)
    dp.message.middleware(injector)
    dp.callback_query.middleware(injector)

    # Order matters: admin first so admin reply / commands take precedence,
    # then registration FSM, then start handlers, then the catch-all questions.
    dp.include_router(admin.router)
    dp.include_router(registration.router)
    dp.include_router(start.router)
    dp.include_router(questions.router)

    # Drop any pending updates from previous runs to avoid double-processing.
    await bot.delete_webhook(drop_pending_updates=True)

    health_runner = await _start_health_server(
        config.PORT,
        db=db,
        db_path=config.DB_PATH,
        restore_token=config.RESTORE_TOKEN,
    )

    stop_event = asyncio.Event()

    def _trigger_stop(*_: Any) -> None:
        log.info("Shutdown signal received.")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            loop.add_signal_handler(sig, _trigger_stop)
        except NotImplementedError:
            # Windows: add_signal_handler is unsupported. signal.signal is
            # the fallback; on Railway (Linux) the loop handler is used.
            signal.signal(sig, _trigger_stop)

    polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
    stop_task = asyncio.create_task(stop_event.wait())

    log.info("Bot started.")
    try:
        done, pending = await asyncio.wait(
            {polling_task, stop_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        # If polling exited on its own (e.g. fatal aiogram error), log it.
        if polling_task in done:
            exc = polling_task.exception()
            if exc:
                log.error("Polling crashed: %r", exc)
        for t in pending:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
    finally:
        log.info("Shutting down...")
        try:
            await dp.stop_polling()
        except Exception:
            pass
        await bot.session.close()
        await health_runner.cleanup()
        await db.close()
        log.info("Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
