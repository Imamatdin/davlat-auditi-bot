"""All keyboard builders.

Inline button callback_data conventions:
  reg:start          start registration
  reg:rereg          re-register
  reg:prog:bakalavr  pick program
  reg:prog:magistr   pick program
  reg:confirm        confirm summary
  reg:restart        restart from name
  reg:cancel         cancel FSM
  admin:reply:<qid>  open reply mode for question <qid>
  admin:bcast:yes    confirm pending broadcast
  admin:bcast:no     cancel pending broadcast
"""
from __future__ import annotations

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


def admin_reply_keyboard(question_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=texts.BTN_REPLY,
                callback_data=f"admin:reply:{question_id}",
            )]
        ]
    )


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=texts.BTN_YES, callback_data="admin:bcast:yes"),
                InlineKeyboardButton(text=texts.BTN_NO, callback_data="admin:bcast:no"),
            ]
        ]
    )
