"""Bot entrypoint.

Runs the aiogram dispatcher alongside a tiny aiohttp healthcheck server in
the same asyncio loop. Railway pings the healthcheck path, keeping the
service from being put to sleep.
"""
from __future__ import annotations

import asyncio
import logging
import signal
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


async def _start_health_server(port: int) -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", _healthcheck)
    app.router.add_get("/healthz", _healthcheck)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logging.getLogger(__name__).info("Healthcheck listening on 0.0.0.0:%s", port)
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

    health_runner = await _start_health_server(config.PORT)

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
