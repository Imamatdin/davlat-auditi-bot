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
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message

from .. import keyboards, texts
from ..config import ADMIN_IDS, BROADCAST_DELAY_SECONDS
from ..db import Database, students_to_csv_rows
from ..utils import (
    build_students_csv,
    humanize_age,
    is_valid_faq_keyword,
    normalize_keyword,
    suggest_faq_keyword,
)

# Unanswered questions shown per /queue page.
_QUEUE_PAGE_SIZE = 5

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


class FaqAdd(StatesGroup):
    keyword = State()
    answer = State()


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
        ),
        reply_markup=keyboards.admin_menu_keyboard(),
    )


# ---------------------------------------------------------------------------
# Admin menu (reply-keyboard buttons -> same actions as the slash commands)
# ---------------------------------------------------------------------------

_ADMIN_MENU_LABELS = {
    texts.BTN_MENU_QUEUE,
    texts.BTN_MENU_STATS,
    texts.BTN_MENU_FAQ_LIST,
    texts.BTN_MENU_FAQ_ADD,
    texts.BTN_MENU_BROADCAST,
    texts.BTN_MENU_EXPORT,
}


# Registered before the FAQ-add and reply text handlers and with no state
# filter, so a menu tap is always handled here (never forwarded to a student
# mid-reply, never eaten as FAQ-add input). State is cleared first so the tap
# navigates cleanly out of any in-flight flow.
@router.message(F.text.in_(_ADMIN_MENU_LABELS), _is_admin)
async def on_admin_menu_button(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    label = message.text
    if label == texts.BTN_MENU_QUEUE:
        await cmd_queue(message, db)
    elif label == texts.BTN_MENU_STATS:
        await cmd_stats(message, db)
    elif label == texts.BTN_MENU_FAQ_LIST:
        await cmd_faq_list(message, db)
    elif label == texts.BTN_MENU_FAQ_ADD:
        await cmd_faq_add(message, state)
    elif label == texts.BTN_MENU_BROADCAST:
        await message.answer(texts.ADMIN_BROADCAST_USAGE)
    elif label == texts.BTN_MENU_EXPORT:
        await cmd_export(message, db)


# ---------------------------------------------------------------------------
# /stats
# ---------------------------------------------------------------------------

@router.message(Command("stats"), _is_admin)
async def cmd_stats(message: Message, db: Database) -> None:
    s = await db.stats()
    await message.answer(
        texts.ADMIN_STATS.format(
            q_total=s["q_total"],
            q_unanswered=s["q_unanswered"],
            q_answered=s["q_answered"],
        )
    )


# ---------------------------------------------------------------------------
# /queue  (worklist of unanswered questions, oldest first, edit-in-place pages)
# ---------------------------------------------------------------------------

async def _render_queue(db: Database, page: int):
    """Build (text, keyboard) for queue `page`. Returns keyboard=None when the
    queue is empty. Page is clamped into range so a stale page index (e.g. the
    last page after questions were answered elsewhere) still renders."""
    total = await db.count_open_questions()
    if total == 0:
        return texts.ADMIN_QUEUE_EMPTY, None

    pages = (total + _QUEUE_PAGE_SIZE - 1) // _QUEUE_PAGE_SIZE
    page = max(0, min(page, pages - 1))
    offset = page * _QUEUE_PAGE_SIZE
    items = await db.get_open_questions(limit=_QUEUE_PAGE_SIZE, offset=offset)

    parts = [texts.ADMIN_QUEUE_HEADER.format(total=total, page=page + 1, pages=pages)]
    ids: list[int] = []
    for i, it in enumerate(items):
        ids.append(it.id)
        if it.kind == "voice":
            body = texts.QUEUE_VOICE_LABEL
        else:
            raw = it.content or ""
            if len(raw) > 200:
                raw = raw[:200] + "..."
            body = _html(raw)
        parts.append(
            texts.ADMIN_QUEUE_ITEM.format(
                idx=offset + i + 1,
                name=_html(it.full_name),
                program=_html(it.program),
                waited=humanize_age(it.created_at),
                body=body,
            )
        )
    kb = keyboards.queue_keyboard(ids, page=page, pages=pages, start_no=offset + 1)
    return "".join(parts), kb


@router.message(Command("queue"), _is_admin)
async def cmd_queue(message: Message, db: Database) -> None:
    text, kb = await _render_queue(db, 0)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("admin:queue:"), _is_admin)
async def cb_queue_page(cq: CallbackQuery, db: Database) -> None:
    try:
        page = int(cq.data.split(":")[-1])
    except (ValueError, IndexError):
        with suppress(TelegramBadRequest):
            await cq.answer()
        return
    text, kb = await _render_queue(db, page)
    # editMessageText keeps the old keyboard when reply_markup is omitted, so
    # pass an explicit empty markup to clear it once the queue drains.
    markup = kb if kb is not None else InlineKeyboardMarkup(inline_keyboard=[])
    with suppress(TelegramBadRequest):
        await cq.message.edit_text(text, reply_markup=markup)
    with suppress(TelegramBadRequest):
        await cq.answer()


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
# FAQ management: /faq_add (FSM), /faq_list, /faq_del
# ---------------------------------------------------------------------------

@router.message(Command("faq_add"), _is_admin)
async def cmd_faq_add(message: Message, state: FSMContext) -> None:
    await state.set_state(FaqAdd.keyword)
    await message.answer(texts.ADMIN_FAQ_ADD_ASK_KEYWORD)


@router.message(Command("cancel"), StateFilter(FaqAdd.keyword, FaqAdd.answer), _is_admin)
async def cmd_cancel_faq(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.ADMIN_FAQ_CANCELLED)


@router.message(FaqAdd.keyword, F.text, _is_admin)
async def faq_add_keyword(message: Message, state: FSMContext, db: Database) -> None:
    raw = message.text or ""
    # /cancel is handled above; any other slash command is not a keyword.
    if raw.startswith("/"):
        await message.answer(texts.ADMIN_FAQ_ADD_KEYWORD_INVALID)
        return
    keyword = normalize_keyword(raw)
    if not is_valid_faq_keyword(keyword):
        await message.answer(texts.ADMIN_FAQ_ADD_KEYWORD_INVALID)
        return
    existed = await db.get_faq(keyword) is not None
    await state.update_data(faq_keyword=keyword, faq_existed=existed)
    await state.set_state(FaqAdd.answer)
    await message.answer(texts.ADMIN_FAQ_ADD_ASK_ANSWER.format(keyword=_html(keyword)))


@router.message(FaqAdd.keyword, _is_admin)
async def faq_add_keyword_other(message: Message) -> None:
    await message.answer(texts.ADMIN_FAQ_ADD_KEYWORD_INVALID)


@router.message(FaqAdd.answer, F.text, _is_admin)
async def faq_add_answer(message: Message, state: FSMContext, db: Database) -> None:
    raw = message.text or ""
    if raw.startswith("/"):
        await message.answer(texts.ADMIN_FAQ_ADD_ANSWER_INVALID)
        return
    answer = raw.strip()
    if not answer:
        await message.answer(texts.ADMIN_FAQ_ADD_ANSWER_INVALID)
        return
    data = await state.get_data()
    keyword = data.get("faq_keyword")
    existed = bool(data.get("faq_existed"))
    if not keyword:
        await state.clear()
        await message.answer(texts.ADMIN_FAQ_ADD_KEYWORD_INVALID)
        return
    # Store the answer raw; it is HTML-escaped at send/display time since the
    # bot's default parse mode is HTML.
    await db.add_faq(keyword=keyword, answer_text=answer, created_by=message.from_user.id)
    await state.clear()
    msg = texts.ADMIN_FAQ_ADD_SAVED.format(keyword=_html(keyword))
    if existed:
        msg += "\n" + texts.ADMIN_FAQ_ADD_OVERWRITE.format(keyword=_html(keyword))
    await message.answer(msg)


@router.message(FaqAdd.answer, _is_admin)
async def faq_add_answer_other(message: Message) -> None:
    await message.answer(texts.ADMIN_FAQ_ADD_ANSWER_INVALID)


@router.message(Command("faq_list"), _is_admin)
async def cmd_faq_list(message: Message, db: Database) -> None:
    faqs = await db.all_faqs()
    if not faqs:
        await message.answer(texts.ADMIN_FAQ_LIST_EMPTY)
        return
    # Render into one or more messages, flushing before Telegram's 4096-char
    # limit so a long FAQ set still lists in full instead of failing to send.
    chunk = texts.ADMIN_FAQ_LIST_HEADER.format(total=len(faqs))
    for f in faqs:
        ans = f.answer_text
        if len(ans) > 200:
            ans = ans[:200] + "..."
        item = texts.ADMIN_FAQ_LIST_ITEM.format(
            keyword=_html(f.keyword), answer=_html(ans)
        )
        if len(chunk) + len(item) > 3500:
            await message.answer(chunk)
            chunk = ""
        chunk += item
    if chunk:
        await message.answer(chunk)


@router.message(Command("faq_del"), _is_admin)
async def cmd_faq_del(message: Message, command: CommandObject, db: Database) -> None:
    keyword = normalize_keyword(command.args or "")
    if not keyword:
        await message.answer(texts.ADMIN_FAQ_DEL_USAGE)
        return
    if await db.delete_faq(keyword):
        await message.answer(texts.ADMIN_FAQ_DEL_OK.format(keyword=_html(keyword)))
    else:
        await message.answer(texts.ADMIN_FAQ_DEL_NOT_FOUND.format(keyword=_html(keyword)))


# /faq typed outside reply mode is a dead-end on its own (Telegram only makes
# the bare "/faq" token tappable, dropping the keyword), so guide the admin.
@router.message(Command("faq"), StateFilter(None), _is_admin)
async def cmd_faq_guidance(message: Message) -> None:
    await message.answer(texts.ADMIN_FAQ_NEED_REPLY_MODE)


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


@router.callback_query(F.data.startswith("admin:faqsug:"), _is_admin)
async def cb_faq_suggest(cq: CallbackQuery, db: Database) -> None:
    """Tap the suggested canned answer -> show it with a Ha/Yo'q confirmation.

    Sending is deferred to cb_faq_send so the admin reviews the full answer
    first. This guards against a keyword false-positive auto-replying to a
    prospective student. The keyword is recomputed from the question text
    against the current FAQ set, then carried into the confirm button so the
    send uses exactly the answer shown here.
    """
    try:
        qid = int(cq.data.split(":")[-1])
    except (ValueError, IndexError):
        with suppress(TelegramBadRequest):
            await cq.answer()
        return

    question = await db.get_question(qid)
    if question is None:
        with suppress(TelegramBadRequest):
            await cq.answer("Savol topilmadi.", show_alert=True)
        return
    if question.answered_at is not None:
        with suppress(TelegramBadRequest):
            await cq.answer(texts.ADMIN_FAQ_SUGGEST_ALREADY, show_alert=True)
        return

    faqs = await db.all_faqs()
    keyword = suggest_faq_keyword(question.content or "", [f.keyword for f in faqs])
    faq = await db.get_faq(keyword) if keyword else None
    if faq is None:
        with suppress(TelegramBadRequest):
            await cq.answer(texts.ADMIN_FAQ_SUGGEST_GONE, show_alert=True)
        return

    await cq.message.answer(
        texts.ADMIN_FAQ_CONFIRM.format(
            keyword=_html(keyword), answer=_html(faq.answer_text)
        ),
        reply_markup=keyboards.faq_confirm_keyboard(qid, keyword),
    )
    with suppress(TelegramBadRequest):
        await cq.answer()


@router.callback_query(F.data.startswith("admin:faqok:"), _is_admin)
async def cb_faq_send(cq: CallbackQuery, db: Database, bot: Bot) -> None:
    """Confirmed (Ha) send of the suggested canned answer."""
    parts = cq.data.split(":")  # admin:faqok:<qid>[:<keyword>]
    try:
        qid = int(parts[2])
    except (ValueError, IndexError):
        with suppress(TelegramBadRequest):
            await cq.answer()
        return
    # Keyword (if carried) holds no ':' by validation, so parts[3] is whole.
    carried_keyword = parts[3] if len(parts) > 3 and parts[3] else None

    question = await db.get_question(qid)
    if question is None:
        await _finish_confirm(cq, "Savol topilmadi.")
        return
    if question.answered_at is not None:
        await _finish_confirm(cq, texts.ADMIN_FAQ_SUGGEST_ALREADY)
        return
    student = await db.get_student(question.user_id)
    if student is None:
        await _finish_confirm(cq, "Foydalanuvchi topilmadi.")
        return

    keyword = carried_keyword
    if keyword is None:
        faqs = await db.all_faqs()
        keyword = suggest_faq_keyword(question.content or "", [f.keyword for f in faqs])
    faq = await db.get_faq(keyword) if keyword else None
    if faq is None:
        await _finish_confirm(cq, texts.ADMIN_FAQ_SUGGEST_GONE)
        return

    body = f"{texts.STUDENT_REPLY_HEADER}\n\n{_html(faq.answer_text)}"
    try:
        await bot.send_message(student.user_id, body)
    except (TelegramForbiddenError, TelegramBadRequest) as exc:
        log.warning("Suggested reply to %s failed: %s", student.user_id, exc)
        await _finish_confirm(cq, texts.ADMIN_REPLY_FAILED)
        return

    await db.mark_question_answered(qid)
    await _mark_question_answered_notifications(bot, db, qid)
    await _finish_confirm(
        cq,
        texts.ADMIN_FAQ_CONFIRM_SENT.format(keyword=_html(keyword)),
        toast=texts.ADMIN_FAQ_SUGGEST_SENT.format(keyword=keyword),
    )


@router.callback_query(F.data.startswith("admin:faqno:"), _is_admin)
async def cb_faq_cancel(cq: CallbackQuery) -> None:
    """Declined (Yo'q): drop the suggestion, leave the question open."""
    await _finish_confirm(cq, texts.ADMIN_FAQ_CONFIRM_CANCELLED)


async def _finish_confirm(
    cq: CallbackQuery, text: str, *, toast: Optional[str] = None
) -> None:
    """Replace the confirmation message with a final status and clear buttons."""
    with suppress(TelegramBadRequest):
        await cq.message.edit_text(
            text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[])
        )
    with suppress(TelegramBadRequest):
        if toast:
            await cq.answer(toast)
        else:
            await cq.answer()


@router.message(Command("cancel"), AdminReply.waiting, _is_admin)
async def cmd_cancel_reply(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.ADMIN_REPLY_CANCELLED)


# Registered before the generic reply_with_text so "/faq <keyword>" in reply
# mode sends a canned answer instead of being rejected as a stray command.
@router.message(Command("faq"), AdminReply.waiting, _is_admin)
async def cmd_faq_in_reply(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    db: Database,
    bot: Bot,
) -> None:
    keyword = normalize_keyword(command.args or "")
    if not keyword:
        await message.answer(texts.ADMIN_FAQ_REPLY_USAGE)
        return  # stay in reply mode
    faq = await db.get_faq(keyword)
    if faq is None:
        await message.answer(
            texts.ADMIN_FAQ_REPLY_NOT_FOUND.format(keyword=_html(keyword))
        )
        return  # stay in reply mode

    data = await state.get_data()
    qid: Optional[int] = data.get("target_question_id")
    target_id: Optional[int] = data.get("target_user_id")
    target_name: str = data.get("target_name") or ""
    if not qid or not target_id:
        await message.answer(texts.ADMIN_REPLY_NO_TARGET)
        await state.clear()
        return

    body = f"{texts.STUDENT_REPLY_HEADER}\n\n{_html(faq.answer_text)}"
    try:
        await bot.send_message(target_id, body)
    except (TelegramForbiddenError, TelegramBadRequest) as exc:
        log.warning("FAQ reply to %s failed: %s", target_id, exc)
        await message.answer(texts.ADMIN_REPLY_FAILED)
        await state.clear()
        return

    await db.mark_question_answered(qid)
    await _mark_question_answered_notifications(bot, db, qid)
    await message.answer(texts.ADMIN_REPLY_SENT.format(name=_html(target_name)))
    await state.clear()


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
    await _mark_question_answered_notifications(bot, db, qid)
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
    await _mark_question_answered_notifications(bot, db, qid)
    await message.answer(texts.ADMIN_REPLY_SENT.format(name=_html(target_name)))
    await state.clear()


@router.message(AdminReply.waiting, _is_admin)
async def reply_unsupported(message: Message) -> None:
    await message.answer(texts.ADMIN_REPLY_UNSUPPORTED)


async def _mark_question_answered_notifications(
    bot: Bot,
    db: Database,
    qid: int,
) -> None:
    """Mark every stored notification for `qid` as answered.

    Appends the "Javob berildi" marker and strips the inline reply button on
    each admin's original notification, including the admin who just replied,
    so the question is never presented as open again (critical when there is
    only one admin: their own notification must close out, not just others').
    """
    notifications = await db.get_notifications(qid)
    # Telegram's editMessageText keeps the existing inline keyboard when
    # reply_markup is omitted from the request, and aiogram's serializer
    # strips reply_markup=None via exclude_none. We therefore send an
    # explicit empty InlineKeyboardMarkup, which Telegram treats as
    # "clear the keyboard."
    cleared = InlineKeyboardMarkup(inline_keyboard=[])
    for n in notifications:
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
