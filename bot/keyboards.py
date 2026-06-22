"""All keyboard builders.

Inline button callback_data conventions:
  reg:start          start registration
  reg:rereg          re-register
  reg:prog:bakalavr  pick program
  reg:prog:magistr   pick program
  reg:confirm        confirm summary
  reg:restart        restart from name
  reg:cancel         cancel FSM
  admin:reply:<qid>          open reply mode for question <qid>
  admin:faqsug:<qid>         show the suggested canned answer for <qid> (asks to confirm)
  admin:faqok:<qid>[:<kw>]   confirmed: send the canned answer for <qid>
  admin:faqno:<qid>          declined: do not send the canned answer
  admin:queue:<page>         jump the /queue worklist to page <page> (edit-in-place)
  admin:bcast:yes            confirm pending broadcast
  admin:bcast:no             cancel pending broadcast
"""
from __future__ import annotations

from typing import Optional

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from . import texts

# ---------------------------------------------------------------------------
# Reply keyboards
# ---------------------------------------------------------------------------

def remove_reply_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts.BTN_SHARE_CONTACT, request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="+998...",
    )


# ---------------------------------------------------------------------------
# Inline keyboards
# ---------------------------------------------------------------------------

def start_keyboard(registered: bool) -> InlineKeyboardMarkup:
    text = texts.BTN_REREGISTER if registered else texts.BTN_REGISTER
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data="reg:start")]]
    )


def program_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_BAKALAVR, callback_data="reg:prog:bakalavr")],
            [InlineKeyboardButton(text=texts.BTN_MAGISTRATURA, callback_data="reg:prog:magistr")],
            [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="reg:cancel")],
        ]
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=texts.BTN_CONFIRM, callback_data="reg:confirm"),
                InlineKeyboardButton(text=texts.BTN_RESTART, callback_data="reg:restart"),
            ],
            [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="reg:cancel")],
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="reg:cancel")]
        ]
    )


def admin_reply_keyboard(
    question_id: int, suggestion: Optional[str] = None
) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=texts.BTN_REPLY,
            callback_data=f"admin:reply:{question_id}",
        )]
    ]
    # When a saved FAQ strongly matches the question, offer a one-tap send
    # above the manual reply button.
    if suggestion:
        rows.insert(0, [InlineKeyboardButton(
            text=texts.BTN_FAQ_SUGGEST.format(keyword=suggestion),
            callback_data=f"admin:faqsug:{question_id}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def faq_confirm_keyboard(question_id: int, keyword: str) -> InlineKeyboardMarkup:
    """Ha / Yo'q confirmation for a suggested canned answer.

    The keyword rides in the "Ha" callback so the send uses exactly the answer
    the admin just reviewed (no recompute drift). callback_data is capped at 64
    bytes by Telegram; if a long keyword would overflow, drop it and let the
    send handler recompute from the question text.
    """
    yes = f"admin:faqok:{question_id}:{keyword}"
    if len(yes.encode("utf-8")) > 64:
        yes = f"admin:faqok:{question_id}"
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=texts.BTN_FAQ_CONFIRM_YES, callback_data=yes),
            InlineKeyboardButton(
                text=texts.BTN_FAQ_CONFIRM_NO,
                callback_data=f"admin:faqno:{question_id}",
            ),
        ]]
    )


def queue_keyboard(
    item_ids: list[int], *, page: int, pages: int, start_no: int
) -> InlineKeyboardMarkup:
    """Worklist keyboard: a numbered reply button per listed question plus a
    prev / refresh / next navigation row. Button "N" maps to the "N." line in
    the message body (start_no is the first displayed number on this page)."""
    rows: list[list[InlineKeyboardButton]] = []
    if item_ids:
        rows.append([
            InlineKeyboardButton(
                text=f"✍️ {start_no + i}",
                callback_data=f"admin:reply:{qid}",
            )
            for i, qid in enumerate(item_ids)
        ])
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text=texts.BTN_PREV, callback_data=f"admin:queue:{page - 1}"
        ))
    nav.append(InlineKeyboardButton(
        text=texts.BTN_REFRESH, callback_data=f"admin:queue:{page}"
    ))
    if page < pages - 1:
        nav.append(InlineKeyboardButton(
            text=texts.BTN_NEXT, callback_data=f"admin:queue:{page + 1}"
        ))
    rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=texts.BTN_YES, callback_data="admin:bcast:yes"),
                InlineKeyboardButton(text=texts.BTN_NO, callback_data="admin:bcast:no"),
            ]
        ]
    )
