"""Admin commands and reply-forwarding flow.

Admin reply flow:
  1. Admin sees a per-question notification with a "Javob yozish" inline button
     (callback_data = "admin:reply:<qid>").
  2. Clicking it puts the admin into AdminReply.waiting FSM state with the
     target question_id, the student's user_id, and the student's name.
  3. The next text or voice message from the admin is forwarded to the
     student, the specific question is marked answered, and every OTHER
     admin's notification for that question gets its inline button removed
     and "Javob berildi" appended so duplicate work is avoided.
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
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message

from .. import keyboards, texts
from ..config import ADMIN_IDS, BROADCAST_DELAY_SECONDS
from ..db import Database, students_to_csv_rows
from ..utils import build_students_csv

# Max characters of the broadcast body we render inside the preview message.
# Telegram's per-message limit is 4096; the surrounding template eats ~80,
# so we cap the inlined preview itself well below that.
_PREVIEW_MAX = 3500

log = logging.getLogger(__name__)
router = Router(name="admin")


class AdminReply(StatesGroup):
    waiting = State()


class Broadcast(StatesGroup):
    confirm = State()


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
    state: FSMContext,
    db: Database,
) -> None:
    text = (command.args or "").strip()
    if not text:
        await message.answer(texts.ADMIN_BROADCAST_USAGE)
        return

    total = len(await db.all_student_ids())
    if total == 0:
        await message.answer(texts.ADMIN_BROADCAST_EMPTY)
        return

    await state.set_state(Broadcast.confirm)
    await state.update_data(broadcast_text=text)

    preview_body = text if len(text) <= _PREVIEW_MAX else text[:_PREVIEW_MAX] + "..."
    await message.answer(
        texts.ADMIN_BROADCAST_PREVIEW.format(
            total=total,
            preview=_html(preview_body),
        ),
        reply_markup=keyboards.broadcast_confirm_keyboard(),
    )


@router.callback_query(Broadcast.confirm, F.data == "admin:bcast:no", _is_admin)
async def cb_broadcast_no(cq: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    with suppress(TelegramBadRequest):
        await cq.message.edit_reply_markup(reply_markup=None)
    await cq.message.answer(texts.ADMIN_BROADCAST_CANCELLED)
    with suppress(TelegramBadRequest):
        await cq.answer()


@router.callback_query(Broadcast.confirm, F.data == "admin:bcast:yes", _is_admin)
async def cb_broadcast_yes(
    cq: CallbackQuery,
    state: FSMContext,
    db: Database,
    bot: Bot,
) -> None:
    data = await state.get_data()
    text: Optional[str] = data.get("broadcast_text")
    await state.clear()
    with suppress(TelegramBadRequest):
        await cq.message.edit_reply_markup(reply_markup=None)
    with suppress(TelegramBadRequest):
        await cq.answer()

    if not text:
        await cq.message.answer(texts.ADMIN_BROADCAST_STALE)
        return

    student_ids = await db.all_student_ids()
    if not student_ids:
        await cq.message.answer(texts.ADMIN_BROADCAST_EMPTY)
        return

    await cq.message.answer(
        texts.ADMIN_BROADCAST_STARTED.format(total=len(student_ids))
    )

    ok = 0
    fail = 0
    for sid in student_ids:
        try:
            # parse_mode=None: send the admin's text as plain text so any
            # unbalanced <tags> they typed don't fail per-recipient under
            # the bot's default HTML parse mode.
            await bot.send_message(sid, text, parse_mode=None)
            ok += 1
        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            log.info("Broadcast to %s failed: %s", sid, exc)
            fail += 1
        except Exception:  # pragma: no cover
            log.exception("Unexpected broadcast error for %s", sid)
            fail += 1
        await asyncio.sleep(BROADCAST_DELAY_SECONDS)

    await cq.message.answer(texts.ADMIN_BROADCAST_DONE.format(ok=ok, fail=fail))


@router.message(Command("cancel"), Broadcast.confirm, _is_admin)
async def cmd_cancel_broadcast(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.ADMIN_BROADCAST_CANCELLED)


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
        qid = int(cq.data.split(":")[-1])
    except (ValueError, IndexError):
        with suppress(TelegramBadRequest):
            await cq.answer("Bad target.", show_alert=True)
        return

    question = await db.get_question(qid)
    if question is None:
        with suppress(TelegramBadRequest):
            await cq.answer("Savol topilmadi.", show_alert=True)
        return

    student = await db.get_student(question.user_id)
    if student is None:
        with suppress(TelegramBadRequest):
            await cq.answer("Foydalanuvchi topilmadi.", show_alert=True)
        return

    await state.set_state(AdminReply.waiting)
    await state.update_data(
        target_question_id=qid,
        target_user_id=student.user_id,
        target_name=student.full_name,
    )

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
    qid: Optional[int] = data.get("target_question_id")
    target_id: Optional[int] = data.get("target_user_id")
    target_name: str = data.get("target_name") or ""
    if not qid or not target_id:
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

    await db.mark_question_answered(qid)
    await _mark_other_admins_answered(bot, db, qid, replying_admin_id=message.from_user.id)
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
    qid: Optional[int] = data.get("target_question_id")
    target_id: Optional[int] = data.get("target_user_id")
    target_name: str = data.get("target_name") or ""
    if not qid or not target_id:
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

    await db.mark_question_answered(qid)
    await _mark_other_admins_answered(bot, db, qid, replying_admin_id=message.from_user.id)
    await message.answer(texts.ADMIN_REPLY_SENT.format(name=_html(target_name)))
    await state.clear()


@router.message(AdminReply.waiting, _is_admin)
async def reply_unsupported(message: Message) -> None:
    await message.answer(texts.ADMIN_REPLY_UNSUPPORTED)


async def _mark_other_admins_answered(
    bot: Bot,
    db: Database,
    qid: int,
    *,
    replying_admin_id: int,
) -> None:
    """Edit the original notification for every admin except the replier.

    Appends the "Javob berildi" marker and strips the inline reply button so
    other admins can see at a glance the question is closed and don't try
    to answer again.
    """
    notifications = await db.get_notifications(qid)
    # Telegram's editMessageText keeps the existing inline keyboard when
    # reply_markup is omitted from the request, and aiogram's serializer
    # strips reply_markup=None via exclude_none. We therefore send an
    # explicit empty InlineKeyboardMarkup, which Telegram treats as
    # "clear the keyboard."
    cleared = InlineKeyboardMarkup(inline_keyboard=[])
    for n in notifications:
        if n.admin_id == replying_admin_id:
            continue
        new_text = n.original_text + texts.NOTIFICATION_ANSWERED_SUFFIX
        try:
            await bot.edit_message_text(
                chat_id=n.admin_id,
                message_id=n.message_id,
                text=new_text,
                reply_markup=cleared,
            )
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            # Common causes: message too old to edit (>48h), admin blocked
            # the bot, original message was deleted. Log and skip.
            log.warning(
                "Could not mark notification answered for admin %s qid=%s: %s",
                n.admin_id, qid, exc,
            )
        except Exception:  # pragma: no cover (defensive)
            log.exception(
                "Unexpected error marking notification answered (admin=%s qid=%s)",
                n.admin_id, qid,
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
