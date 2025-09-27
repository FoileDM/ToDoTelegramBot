"""Основной модуль для запуска бота."""

from __future__ import annotations

import asyncio
import logging

import uvloop
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram_dialog import setup_dialogs, DialogManager, StartMode

from core.config import settings
from dialogs.start import router as start_router
from dialogs.task_add import add_task_dialog, AddTaskSG
from handlers.tasks_list import router as tasks_router
from middlewares.rate_limit import RateLimitMiddleware
from web.health import make_app


async def run_health_server():
    """
    Создает и запускает сервер проверки состояния (health server).

    Args:
        Нет аргументов.

    Returns:
        None: Функция не возвращает значения.

    Raises:
        OSError: Если возникают ошибки при настройке или запуске сервера.
    """
    app = make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.health_port)
    await site.start()


async def main():
    """
    Запускает основной цикл работы бота.

    Настраивает соединение с ботом, регистрирует middleware, подключает маршрутизаторы
    и запускает механизм обработки сообщений, включая фоновые задачи.

    Raises:
        Exception: Любая ошибка, возникающая во время работы основного цикла или настройки.
    """
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    # middleware
    dp.message.middleware(RateLimitMiddleware(limit=5, per_seconds=10))
    dp.callback_query.middleware(RateLimitMiddleware(limit=10, per_seconds=10))

    # routers
    dp.include_router(start_router)
    dp.include_router(tasks_router)
    dp.include_router(add_task_dialog)  # Dialog в v2 — это Router

    # инициализация диалогов (v2)
    setup_dialogs(dp)

    # background health http server
    asyncio.create_task(run_health_server())

    # команда для запуска мастера добавления задачи
    @dp.message(Command("add"))
    async def start_add_dialog(message: Message, dialog_manager: DialogManager):
        """
        Запускает диалог добавления задачи.

        Args:
            message (Message): Объект сообщения от пользователя.
            dialog_manager (DialogManager): Менеджер диалога.
        """
        await dialog_manager.start(AddTaskSG.title, mode=StartMode.RESET_STACK)

    await dp.start_polling(bot)


if __name__ == "__main__":
    uvloop.install()
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
