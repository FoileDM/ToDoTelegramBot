"""Основной модуль для запуска бота."""

from __future__ import annotations

import asyncio
import logging

import uvloop
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram_dialog import setup_dialogs, DialogManager, StartMode
from aiohttp import web

from core.config import settings
from dialogs.add_category import add_category_dialog, AddCategorySG
from dialogs.category_delete import DeleteCategorySG, delete_category_dialog
from dialogs.category_edit import EditCategorySG, edit_category_dialog
from dialogs.start import router as start_router
from dialogs.task_add import add_task_dialog, AddTaskSG
from dialogs.task_delete import DeleteTaskSG, delete_task_dialog
from dialogs.task_edit import edit_task_dialog, EditTaskSG
from dialogs.task_status import change_task_status_dialog, ChangeTaskStatusSG
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
    dp.include_router(add_task_dialog)
    dp.include_router(edit_task_dialog)
    dp.include_router(delete_task_dialog)
    dp.include_router(change_task_status_dialog)
    dp.include_router(add_category_dialog)
    dp.include_router(edit_category_dialog)
    dp.include_router(delete_category_dialog)

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

    @dp.message(Command("edittask"))
    async def start_edit_dialog(message: Message, dialog_manager: DialogManager):
        """
        Запускает диалог редактирования задачи.

        Args:
            message (Message): Сообщение от пользователя.
            dialog_manager (DialogManager): Менеджер управления диалогом.
        """
        await dialog_manager.start(EditTaskSG.choose_task, mode=StartMode.RESET_STACK)

    @dp.message(Command("status"))
    async def start_change_status_dialog(
            message: Message, dialog_manager: DialogManager
    ) -> None:
        """Запускает диалог изменения статуса задачи.

        Args:
            message: Сообщение пользователя, инициирующее команду.
            dialog_manager: Менеджер диалога для запуска сценария.
        """
        await dialog_manager.start(
            ChangeTaskStatusSG.choose_task, mode=StartMode.RESET_STACK
        )

    @dp.message(Command("deltask"))
    async def start_delete_dialog(message: Message, dialog_manager: DialogManager) -> None:
        """
        Запускает диалог удаления задачи.

        Args:
            message: Message: Сообщение от пользователя, инициирующее команду.
            dialog_manager: DialogManager: Менеджер диалогов для управления состояниями диалога.
        """
        await dialog_manager.start(DeleteTaskSG.choose_task, mode=StartMode.RESET_STACK)

    @dp.message(Command("addcat"))
    async def start_add_category(message: Message, dialog_manager: DialogManager):
        """
        Запускает диалог добавления задачи.

        Args:
            message (Message): Объект сообщения от пользователя.
            dialog_manager (DialogManager): Менеджер диалога.
        """
        await dialog_manager.start(AddCategorySG.name, mode=StartMode.RESET_STACK)

    @dp.message(Command("editcat"))
    async def start_edit_category(message: Message, dialog_manager: DialogManager):
        """
        Начинает процесс редактирования категории.

        Args:
            message (Message): Сообщение от пользователя.
            dialog_manager (DialogManager): Менеджер диалога.
        """
        await dialog_manager.start(
            EditCategorySG.choose_category, mode=StartMode.RESET_STACK
        )

    @dp.message(Command("delcat"))
    async def start_delete_category(message: Message, dialog_manager: DialogManager) -> None:
        """
        Запускает диалог удаления категории.

        Args:
            message (Message): Объект сообщения, инициировавшего команду.
            dialog_manager (DialogManager): Менеджер диалогов.
        """
        await dialog_manager.start(
            DeleteCategorySG.choose_category, mode=StartMode.RESET_STACK
        )

    await dp.start_polling(bot)


if __name__ == "__main__":
    uvloop.install()
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
