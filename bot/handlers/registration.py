"""FSM-driven registration flow.

States walk the student through: name -> phone -> program -> region -> confirm.
On confirmation the row is upserted and admins are notified.
"""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import Optional

import aiosqlite
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .. import keyboards, texts
from ..config import ADMIN_IDS
from ..db import Database
from .start import send_main_menu
from ..utils import (
    clean_name,
    clean_region,
    is_region_valid,
    normalize_phone,
    validate_name,
)

log = logging.getLogger(__name__)
router = Router(name="registration")


class Reg(StatesGroup):
    name = State()
    phone = State()
    program = State()
    region = State()
    confirm = State()


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "reg:start")
async def cb_start_registration(cq: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(Reg.name)
    await cq.message.answer(texts.ASK_NAME, reply_markup=keyboards.cancel_keyboard())
    with suppress(TelegramBadRequest):
        await cq.answer()


@router.callback_query(F.data == "reg:cancel")
async def cb_cancel(cq: CallbackQuery, state: FSMContext, db: Database) -> None:
    await state.clear()
    await cq.message.answer(
        texts.REG_CANCELLED,
        reply_markup=keyboards.remove_reply_keyboard(),
    )
    await send_main_menu(cq.message, db, cq.from_user.id)
    with suppress(TelegramBadRequest):
        await cq.answer()


@router.message(Command("cancel"), StateFilter(Reg))
async def cmd_cancel(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    await message.answer(
        texts.REG_CANCELLED,
        reply_markup=keyboards.remove_reply_keyboard(),
    )
    await send_main_menu(message, db, message.from_user.id)


# ---------------------------------------------------------------------------
# Name
# ---------------------------------------------------------------------------

@router.message(Reg.name, F.text)
async def step_name(message: Message, state: FSMContext) -> None:
    if not validate_name(message.text or ""):
        await message.answer(texts.ERR_NAME_INVALID)
        return

    await state.update_data(name=clean_name(message.text))
    await state.set_state(Reg.phone)
    await message.answer(texts.ASK_PHONE, reply_markup=keyboards.contact_keyboard())


@router.message(Reg.name)
async def step_name_non_text(message: Message) -> None:
    await message.answer(texts.ASK_NAME)


# ---------------------------------------------------------------------------
# Phone
# ---------------------------------------------------------------------------

@router.message(Reg.phone, F.contact)
async def step_phone_contact(message: Message, state: FSMContext, db: Database) -> None:
    # When a user shares a contact, accept only their own number to prevent
    # someone registering under a friend's contact card.
    contact = message.contact
    if contact.user_id and contact.user_id != message.from_user.id:
        await message.answer(texts.ERR_PHONE_INVALID, reply_markup=keyboards.contact_keyboard())
        return
    phone = normalize_phone(contact.phone_number or "")
    if phone is None:
        await message.answer(texts.ERR_PHONE_INVALID, reply_markup=keyboards.contact_keyboard())
        return
    await _advance_from_phone(message, state, db, phone)


@router.message(Reg.phone, F.text)
async def step_phone_text(message: Message, state: FSMContext, db: Database) -> None:
    phone = normalize_phone(message.text or "")
    if phone is None:
        await message.answer(texts.ERR_PHONE_INVALID, reply_markup=keyboards.contact_keyboard())
        return
    await _advance_from_phone(message, state, db, phone)


@router.message(Reg.phone)
async def step_phone_other(message: Message) -> None:
    await message.answer(texts.ASK_PHONE, reply_markup=keyboards.contact_keyboard())


async def _advance_from_phone(
    message: Message, state: FSMContext, db: Database, phone: str
) -> None:
    # One phone = one Telegram account. Block the form before the user fills
    # out program + region only to be rejected at confirm time.
    existing = await db.get_student_by_phone(phone)
    if existing is not None and existing.user_id != message.from_user.id:
        await message.answer(
            texts.ERR_PHONE_TAKEN, reply_markup=keyboards.contact_keyboard()
        )
        return

    await state.update_data(phone=phone)
    await state.set_state(Reg.program)
    # Telegram requires a separate message to dismiss the reply keyboard,
    # since inline keyboards do not displace it. Send a brief acknowledgement
    # message with ReplyKeyboardRemove, then the actual prompt with the
    # inline program buttons.
    await message.answer(
        f"Telefon qabul qilindi: <code>{_html(phone)}</code>",
        reply_markup=keyboards.remove_reply_keyboard(),
    )
    await message.answer(texts.ASK_PROGRAM, reply_markup=keyboards.program_keyboard())


# ---------------------------------------------------------------------------
# Program
# ---------------------------------------------------------------------------

@router.callback_query(Reg.program, F.data.startswith("reg:prog:"))
async def step_program(cq: CallbackQuery, state: FSMContext) -> None:
    choice = cq.data.split(":")[-1]
    if choice == "bakalavr":
        program = texts.PROGRAM_BAKALAVR
    elif choice == "magistr":
        program = texts.PROGRAM_MAGISTRATURA
    else:
        with suppress(TelegramBadRequest):
            await cq.answer()
        return

    await state.update_data(program=program)
    await state.set_state(Reg.region)
    with suppress(TelegramBadRequest):
        await cq.message.edit_reply_markup(reply_markup=None)
    await cq.message.answer(texts.ASK_REGION, reply_markup=keyboards.cancel_keyboard())
    with suppress(TelegramBadRequest):
        await cq.answer()


@router.message(Reg.program)
async def step_program_text(message: Message) -> None:
    await message.answer(texts.ASK_PROGRAM, reply_markup=keyboards.program_keyboard())


# ---------------------------------------------------------------------------
# Region
# ---------------------------------------------------------------------------

@router.message(Reg.region, F.text)
async def step_region(message: Message, state: FSMContext) -> None:
    if not is_region_valid(message.text or ""):
        await message.answer(texts.ERR_REGION_SHORT)
        return
    await state.update_data(region=clean_region(message.text))
    await state.set_state(Reg.confirm)
    data = await state.get_data()
    await message.answer(
        texts.CONFIRM_TEMPLATE.format(
            title=texts.CONFIRM_TITLE,
            name=_html(data["name"]),
            phone=_html(data["phone"]),
            program=_html(data["program"]),
            region=_html(data["region"]),
        ),
        reply_markup=keyboards.confirm_keyboard(),
    )


@router.message(Reg.region)
async def step_region_non_text(message: Message) -> None:
    await message.answer(texts.ASK_REGION)


# ---------------------------------------------------------------------------
# Confirm / restart
# ---------------------------------------------------------------------------

@router.callback_query(Reg.confirm, F.data == "reg:confirm")
async def cb_confirm(cq: CallbackQuery, state: FSMContext, db: Database, bot: Bot) -> None:
    data = await state.get_data()
    user = cq.from_user
    try:
        student = await db.upsert_student(
            user_id=user.id,
            username=user.username,
            full_name=data["name"],
            phone=data["phone"],
            program=data["program"],
            region=data["region"],
        )
    except aiosqlite.IntegrityError:
        # Another user claimed this phone between phone-step and confirm.
        # Bounce back to the phone step instead of wiping the whole form.
        await state.set_state(Reg.phone)
        with suppress(TelegramBadRequest):
            await cq.message.edit_reply_markup(reply_markup=None)
        await cq.message.answer(texts.ERR_PHONE_TAKEN)
        await cq.message.answer(
            texts.ASK_PHONE, reply_markup=keyboards.contact_keyboard()
        )
        with suppress(TelegramBadRequest):
            await cq.answer()
        return
    await state.clear()
    with suppress(TelegramBadRequest):
        await cq.message.edit_reply_markup(reply_markup=None)
    await cq.message.answer(
        texts.REG_SUCCESS.format(name=_html(student.full_name)),
        reply_markup=keyboards.remove_reply_keyboard(),
    )
    with suppress(TelegramBadRequest):
        await cq.answer("OK")

    total = await db.total_students()
    await _notify_admins_new_registration(bot, student, total)


@router.callback_query(Reg.confirm, F.data == "reg:restart")
async def cb_restart(cq: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(Reg.name)
    with suppress(TelegramBadRequest):
        await cq.message.edit_reply_markup(reply_markup=None)
    await cq.message.answer(texts.REG_RESTARTED)
    await cq.message.answer(texts.ASK_NAME, reply_markup=keyboards.cancel_keyboard())
    with suppress(TelegramBadRequest):
        await cq.answer()


# ---------------------------------------------------------------------------
# Admin notification
# ---------------------------------------------------------------------------

async def _notify_admins_new_registration(bot: Bot, student, total: int) -> None:
    body = texts.ADMIN_NEW_REGISTRATION.format(
        count=total,
        name=_html(student.full_name),
        phone=_html(student.phone),
        program=_html(student.program),
        region=_html(student.region),
        username=_html(student.username or "yo'q"),
        user_id=student.user_id,
        registered_at=_html(student.registered_at),
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, body)
        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            log.warning("Failed to notify admin %s of registration: %s", admin_id, exc)
        except Exception:  # pragma: no cover (defensive)
            log.exception("Unexpected error notifying admin %s", admin_id)


def _html(text: Optional[str]) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
