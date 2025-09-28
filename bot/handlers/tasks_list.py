"""Маршруты обработчиков сообщений для задач и категорий."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from services.api import BackendAPI

from utils.fmt import fmt_task_line

router = Router(name="tasks")


@router.message(F.text == "Мои задачи")
async def list_tasks(message: Message):
    """
    Обрабатывает запрос пользователя на отображение списка задач.

    Args:
        message (Message): Сообщение от пользователя, содержащее текст команды.

    Raises:
        Exception: Если возникла ошибка при запросе списка задач.
    """
    tg_id = message.from_user.id
    api = BackendAPI()
    try:
        page = 1
        resp = await api.list_tasks(tg_id=tg_id, page=page)
        items = resp.get("results", [])
        if not items:
            await message.answer("Пока пусто. Нажми «Добавить задачу».")
            return
        lines = [fmt_task_line(t) for t in items[:10]]
        await message.answer("\n".join(lines))
        await message.answer("Для редактирования задачи воспользуйся командой /edittask.")
    except Exception as e:
        await message.answer(f"Ошибка запроса задач: {e}")
    finally:
        await api.aclose()


@router.message(F.text == "Мои категории")
async def list_categories(message: Message):
    """
    Обрабатывает запрос на список категорий пользователя.

    Принимает команду "Мои категории" и возвращает список категорий,
    если они существуют. В случае ошибки выводит сообщение об ошибке.

    Args:
        message (Message): Сообщение от пользователя в чате.

    Raises:
        Exception: Исключение может быть вызвано при ошибках запроса или
            выполнения API-операций.
    """
    tg_id = message.from_user.id
    api = BackendAPI()
    try:
        cats = await api.list_categories(tg_id=tg_id)
        if not cats:
            await message.answer("Категорий нет.")
            return
        txt = "\n".join(f"• {c['name']}" for c in cats)
        await message.answer(txt)
    except Exception as e:
        await message.answer(f"Ошибка запроса категорий: {e}")
    finally:
        await api.aclose()


@router.message(F.text == "Добавить задачу")
async def add_task_hint(message: Message) -> None:
    """
    Обрабатывает сообщение для подсказки добавления задачи.

    Args:
        message (Message): Входящее сообщение от пользователя.
    """
    await message.answer("Введи /add чтобы создать задачу.")


@router.message(F.text == "Добавить категорию")
async def add_category_hint(message: Message) -> None:
    """
    Отправляет пользователю подсказку для добавления новой категории.

    Args:
        message (Message): Сообщение от пользователя.
    """
    await message.answer("Введи /addcat чтобы создать категорию.")


@router.message(F.text == "Редактировать задачу")
async def edit_task_hint(message: Message) -> None:
    """
    Обрабатывает сообщение с текстом "Редактировать задачу".

    Args:
        message (Message): Сообщение от пользователя.
    """
    await message.answer("Введи /edittask чтобы изменить существующую задачу.")
