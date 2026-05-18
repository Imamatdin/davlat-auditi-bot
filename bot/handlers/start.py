"""/start and /info handlers."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from .. import keyboards, texts
from ..db import Database

router = Router(name="start")


async def send_main_menu(message: Message, db: Database, user_id: int) -> None:
    """Send the welcome view to `user_id` via reply on `message`.

    Reused by /start, /cancel, and the inline cancel button so users always
    land back on the same main menu after bailing out of a flow.
    """
    student = await db.get_student(user_id)
    if student is None:
        await message.answer(
            texts.WELCOME,
            reply_markup=keyboards.start_keyboard(registered=False),
        )
    else:
        await message.answer(
            texts.WELCOME_REGISTERED.format(name=_html_escape(student.full_name)),
            reply_markup=keyboards.start_keyboard(registered=True),
        )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database) -> None:
    # /start always wipes any in-flight FSM (registration, admin reply mode, etc).
    await state.clear()
    await send_main_menu(message, db, message.from_user.id)


@router.message(Command("info"))
async def cmd_info(message: Message, db: Database) -> None:
    student = await db.get_student(message.from_user.id)
    if student is None:
        await message.answer(texts.INFO_NOT_REGISTERED)
        return
    await message.answer(
        texts.INFO_TEMPLATE.format(
            name=_html_escape(student.full_name),
            phone=_html_escape(student.phone),
            program=_html_escape(student.program),
            region=_html_escape(student.region),
            registered_at=_html_escape(student.registered_at),
        )
    )


def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
