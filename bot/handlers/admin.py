"""Admin commands and reply-forwarding flow.

Admin reply flow:
  1. Admin sees a question notification with a "Javob yozish" inline button.
  2. Clicking it puts the admin into AdminReply.waiting FSM state with the
     target student's user_id stored in state.data["target_user_id"].
  3. The next text or voice message from the admin is forwarded to the
     student, the question queue for that student is marked answered, and the
     state is cleared.
  4. Admin may /cancel to exit reply mode.

Non-admin attempts at admin commands are silently ignored.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from .. import texts
from ..config import ADMIN_IDS, BROADCAST_DELAY_SECONDS
from ..db import Database, students_to_csv_rows
from ..utils import build_students_csv

log = logging.getLogger(__name__)
router = Router(name="admin")


class AdminReply(StatesGroup):
    waiting = State()


def _is_admin(message_or_cq) -> bool:
    user = getattr(message_or_cq, "from_user", None)
    return user is not None and user.id in ADMIN_IDS


# ---------------------------------------------------------------------------
# /admin dashboard
# ---------------------------------------------------------------------------

@router.message(Command("admin"), _is_admin)
async def cmd_admin(message: Message, db: Database) -> None:
    s = await db.stats()
    await message.answer(
        texts.ADMIN_DASHBOARD.format(
            total=s["total"],
            bakalavr=s["bakalavr"],
            magistr=s["magistr"],
            q_total=s["q_total"],
            q_unanswered=s["q_unanswered"],
        )
    )


# ---------------------------------------------------------------------------
# /broadcast
# ---------------------------------------------------------------------------

@router.message(Command("broadcast"), _is_admin)
async def cmd_broadcast(
    message: Message,
    command: CommandObject,
    db: Database,
    bot: Bot,
) -> None:
    text = (command.args or "").strip()
    if not text:
        await message.answer(texts.ADMIN_BROADCAST_USAGE)
        return

    student_ids = await db.all_student_ids()
    if not student_ids:
        await message.answer(texts.ADMIN_BROADCAST_EMPTY)
        return

    await message.answer(texts.ADMIN_BROADCAST_STARTED.format(total=len(student_ids)))

    ok = 0
    fail = 0
    for sid in student_ids:
        try:
            await bot.send_message(sid, text)
            ok += 1
        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            log.info("Broadcast to %s failed: %s", sid, exc)
            fail += 1
        except Exception:  # pragma: no cover
            log.exception("Unexpected broadcast error for %s", sid)
            fail += 1
        await asyncio.sleep(BROADCAST_DELAY_SECONDS)

    await message.answer(texts.ADMIN_BROADCAST_DONE.format(ok=ok, fail=fail))


# ---------------------------------------------------------------------------
# /export
# ---------------------------------------------------------------------------

@router.message(Command("export"), _is_admin)
async def cmd_export(message: Message, db: Database) -> None:
    students = await db.all_students()
    if not students:
        await message.answer(texts.ADMIN_EXPORT_EMPTY)
        return
    rows = students_to_csv_rows(students)
    payload = build_students_csv(rows)
    filename = f"davlat_auditi_students_{len(students)}.csv"
    await message.answer_document(
        BufferedInputFile(payload, filename=filename),
        caption=texts.ADMIN_EXPORT_CAPTION.format(total=len(students)),
    )


# ---------------------------------------------------------------------------
# Reply mode
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("admin:reply:"), _is_admin)
async def cb_open_reply(cq: CallbackQuery, state: FSMContext, db: Database) -> None:
    try:
        target_id = int(cq.data.split(":")[-1])
    except (ValueError, IndexError):
        with suppress(TelegramBadRequest):
            await cq.answer("Bad target.", show_alert=True)
        return

    student = await db.get_student(target_id)
    if student is None:
        with suppress(TelegramBadRequest):
            await cq.answer("Foydalanuvchi topilmadi.", show_alert=True)
        return

    await state.set_state(AdminReply.waiting)
    await state.update_data(target_user_id=target_id, target_name=student.full_name)

    await cq.message.answer(
        texts.ADMIN_REPLY_PROMPT.format(name=_html(student.full_name))
    )
    with suppress(TelegramBadRequest):
        await cq.answer()


@router.message(Command("cancel"), AdminReply.waiting, _is_admin)
async def cmd_cancel_reply(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.ADMIN_REPLY_CANCELLED)


@router.message(AdminReply.waiting, F.text, _is_admin)
async def reply_with_text(
    message: Message,
    state: FSMContext,
    db: Database,
    bot: Bot,
) -> None:
    # Don't forward bot commands as replies. /cancel is already handled above;
    # any other slash command is almost certainly a typo, not the intended
    # reply text.
    if message.text.startswith("/"):
        await message.answer(texts.ADMIN_REPLY_UNSUPPORTED)
        return

    data = await state.get_data()
    target_id: Optional[int] = data.get("target_user_id")
    target_name: str = data.get("target_name") or ""
    if not target_id:
        await message.answer(texts.ADMIN_REPLY_NO_TARGET)
        await state.clear()
        return

    body = f"{texts.STUDENT_REPLY_HEADER}\n\n{_html(message.text)}"
    try:
        await bot.send_message(target_id, body)
    except (TelegramForbiddenError, TelegramBadRequest) as exc:
        log.warning("Reply to %s failed: %s", target_id, exc)
        await message.answer(texts.ADMIN_REPLY_FAILED)
        await state.clear()
        return

    await db.mark_questions_answered(target_id)
    await message.answer(texts.ADMIN_REPLY_SENT.format(name=_html(target_name)))
    await state.clear()


@router.message(AdminReply.waiting, F.voice, _is_admin)
async def reply_with_voice(
    message: Message,
    state: FSMContext,
    db: Database,
    bot: Bot,
) -> None:
    data = await state.get_data()
    target_id: Optional[int] = data.get("target_user_id")
    target_name: str = data.get("target_name") or ""
    if not target_id:
        await message.answer(texts.ADMIN_REPLY_NO_TARGET)
        await state.clear()
        return

    try:
        await bot.send_message(target_id, texts.STUDENT_REPLY_HEADER)
        await bot.send_voice(target_id, message.voice.file_id)
    except (TelegramForbiddenError, TelegramBadRequest) as exc:
        log.warning("Voice reply to %s failed: %s", target_id, exc)
        await message.answer(texts.ADMIN_REPLY_FAILED)
        await state.clear()
        return

    await db.mark_questions_answered(target_id)
    await message.answer(texts.ADMIN_REPLY_SENT.format(name=_html(target_name)))
    await state.clear()


@router.message(AdminReply.waiting, _is_admin)
async def reply_unsupported(message: Message) -> None:
    await message.answer(texts.ADMIN_REPLY_UNSUPPORTED)


def _html(text: Optional[str]) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
