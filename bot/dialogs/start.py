"""Start dialog"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup

from services.api import BackendAPI

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Обрабатывает команду /start.

    Args:
        message (Message): Объект сообщения Telegram.

    Raises:
        Exception: Ошибка при регистрации пользователя.
    """
    tg_id = message.from_user.id
    username = message.from_user.username
    api = BackendAPI()
    try:
        await api.register(tg_id=tg_id, username=username)
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Мои задачи"), KeyboardButton(text="Добавить задачу")],
                [KeyboardButton(text="Мои категории")],
            ],
            resize_keyboard=True,
        )
        await message.answer("Готово. Чем займёмся?", reply_markup=kb)
    except Exception as e:
        await message.answer(f"Не удалось зарегистрироваться: {e}")
    finally:
        await api.aclose()
