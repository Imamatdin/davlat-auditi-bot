"""Student-side question handling.

Catches text and voice messages from registered students that are NOT part of
any active FSM state, persists them, and notifies admins with a reply button.
"""
from __future__ import annotations

import logging
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from .. import keyboards, texts
from ..config import ADMIN_IDS
from ..db import Database, Student

log = logging.getLogger(__name__)
router = Router(name="questions")

# Max questions any single student may submit in a rolling 1-hour window.
# Defends against floods without throttling legitimate Q&A sessions.
QUESTIONS_PER_HOUR = 10


# Filter: skip messages from any admin so admin-side handlers can claim them
# without this catch-all swallowing /admin, /broadcast, etc.
def _is_non_admin(message: Message) -> bool:
    return message.from_user is not None and message.from_user.id not in ADMIN_IDS


@router.message(F.text, _is_non_admin)
async def on_text_question(
    message: Message,
    state: FSMContext,
    db: Database,
    bot: Bot,
) -> None:
    # State guard: if the user is mid-registration, do nothing here. aiogram
    # routes state-bound handlers first, but we double-check for safety in
    # case ordering changes.
    if await state.get_state() is not None:
        return

    # Unknown slash commands: nudge unregistered users to register, otherwise
    # stay silent (don't forward stray /foo to admins as if they were questions).
    text = message.text or ""
    if text.startswith("/"):
        student = await db.get_student(message.from_user.id)
        if student is None:
            await message.answer(texts.NEED_REGISTRATION)
        return

    student = await db.get_student(message.from_user.id)
    if student is None:
        await message.answer(texts.NEED_REGISTRATION)
        return

    if await db.count_recent_questions(student.user_id, hours=1) >= QUESTIONS_PER_HOUR:
        await message.answer(texts.RATE_LIMITED)
        return

    qid = await db.add_text_question(student.user_id, text)
    await message.answer(texts.QUESTION_RECEIVED_TEXT)
    await _notify_admins_text(bot, db, student, qid, text)


@router.message(F.voice, _is_non_admin)
async def on_voice_question(
    message: Message,
    state: FSMContext,
    db: Database,
    bot: Bot,
) -> None:
    if await state.get_state() is not None:
        return

    student = await db.get_student(message.from_user.id)
    if student is None:
        await message.answer(texts.NEED_REGISTRATION)
        return

    if await db.count_recent_questions(student.user_id, hours=1) >= QUESTIONS_PER_HOUR:
        await message.answer(texts.RATE_LIMITED)
        return

    file_id = message.voice.file_id
    qid = await db.add_voice_question(student.user_id, file_id)
    await message.answer(texts.QUESTION_RECEIVED_VOICE)
    await _notify_admins_voice(bot, db, student, qid, file_id, message.voice.duration)


# Anything other than text or voice from a non-admin gets a nudge so users
# don't think the bot died when they paste a sticker.
@router.message(_is_non_admin)
async def on_unsupported(message: Message, state: FSMContext, db: Database) -> None:
    if await state.get_state() is not None:
        return
    student = await db.get_student(message.from_user.id)
    if student is None:
        await message.answer(texts.NEED_REGISTRATION)
        return
    await message.answer(texts.UNSUPPORTED_MESSAGE)


# ---------------------------------------------------------------------------
# Admin notifications
# ---------------------------------------------------------------------------

async def _notify_admins_text(
    bot: Bot, db: Database, student: Student, qid: int, text: str
) -> None:
    header = texts.ADMIN_NEW_QUESTION_TEXT.format(
        qid=qid,
        name=_html(student.full_name),
        program=_html(student.program),
        phone=_html(student.phone),
        username=_html(student.username or "yo'q"),
        user_id=student.user_id,
        text=_html(text),
    )
    kb = keyboards.admin_reply_keyboard(qid)
    for admin_id in ADMIN_IDS:
        try:
            sent = await bot.send_message(admin_id, header, reply_markup=kb)
        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            log.warning("Failed to notify admin %s of text question: %s", admin_id, exc)
            continue
        except Exception:  # pragma: no cover
            log.exception("Unexpected error notifying admin %s of text question", admin_id)
            continue
        await db.add_notification(
            question_id=qid,
            admin_id=admin_id,
            message_id=sent.message_id,
            original_text=header,
        )


async def _notify_admins_voice(
    bot: Bot,
    db: Database,
    student: Student,
    qid: int,
    file_id: str,
    duration: Optional[int],
) -> None:
    # Header carries metadata + the reply button. Voice goes in a separate
    # message below it, with no button: this keeps the reply button on an
    # editable text message so edit_message_text can mark it answered.
    header = texts.ADMIN_NEW_QUESTION_VOICE.format(
        qid=qid,
        name=_html(student.full_name),
        program=_html(student.program),
        phone=_html(student.phone),
        username=_html(student.username or "yo'q"),
        user_id=student.user_id,
    )
    if duration is not None:
        header = f"{header}\nDavomiyligi: {duration} soniya"
    kb = keyboards.admin_reply_keyboard(qid)
    for admin_id in ADMIN_IDS:
        try:
            sent = await bot.send_message(admin_id, header, reply_markup=kb)
            await bot.send_voice(admin_id, file_id)
        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            log.warning("Failed to notify admin %s of voice question: %s", admin_id, exc)
            continue
        except Exception:  # pragma: no cover
            log.exception("Unexpected error notifying admin %s of voice question", admin_id)
            continue
        await db.add_notification(
            question_id=qid,
            admin_id=admin_id,
            message_id=sent.message_id,
            original_text=header,
        )


def _html(text: Optional[str]) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
