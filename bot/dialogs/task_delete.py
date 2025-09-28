"""Диалог удаления задач."""

from __future__ import annotations

from typing import Any

from aiogram import Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Back, Button, Cancel, ScrollingGroup, Select
from aiogram_dialog.widgets.text import Const, Format
from services.api import BackendAPI, BackendError


class DeleteTaskSG(StatesGroup):
    """
    Группа состояний для удаления задачи.

    Предназначена для управления последовательностью состояний при удалении задачи.

    Атрибуты:
        choose_task (State): Состояние выбора задачи для удаления.
        confirm (State): Состояние подтверждения удаления задачи.
    """
    choose_task = State()
    confirm = State()


async def tasks_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    """
    Получить список задач для диалог-менеджера.

    Функция обращается к API для получения списка задач пользователя, форматирует
    их и сохраняет сырые данные в диалоге. Возвращает задачи в виде списка словарей
    с идентификатором и меткой, текстовым списком задач и флагом наличия задач.

    Args:
        dialog_manager (DialogManager): Менеджер диалогов пользователя.
        **_ (Any): Дополнительные параметры, которые игнорируются.

    Returns:
        dict[str, Any]: Словарь с форматированными задачами, текстовым представлением
        задач и булевым флагом наличия задач.
    """

    api = BackendAPI()
    tg_id = dialog_manager.event.from_user.id
    try:
        response = await api.list_tasks(tg_id=tg_id, page=1)
        tasks: list[dict[str, Any]] = response.get("results", [])
        dialog_manager.dialog_data["tasks_raw"] = tasks
        items: list[dict[str, str]] = []
        lines: list[str] = []
        for task in tasks:
            task_id = str(task.get("id"))
            title = task.get("title", "Без названия")
            items.append({"id": task_id, "label": f"#{task_id} — {title}"})
            lines.append(f"#{task_id}: {title}")
        return {
            "tasks": items,
            "tasks_text": "\n".join(lines) if lines else "Задач пока нет.",
            "has_tasks": bool(items),
        }
    finally:
        await api.aclose()


async def on_task_selected(
        callback: CallbackQuery,
        _: Select,
        manager: DialogManager,
        item_id: str,
) -> None:
    """
    Обрабатывает выбор задачи пользователем и переключает на подтверждение удаления.

    Args:
        callback (CallbackQuery): Объект обратного вызова от пользователя.
        _ (Select): Выбор элемента в диалоге.
        manager (DialogManager): Менеджер диалогов.
        item_id (str): Идентификатор выбранной задачи.

    Raises:
        Any: Показывает сообщение об ошибке, если задача не найдена.
    """
    tasks: list[dict[str, Any]] = manager.dialog_data.get("tasks_raw", [])
    selected = next((task for task in tasks if str(task.get("id")) == item_id), None)
    if selected is None:
        await callback.answer("Не удалось найти задачу", show_alert=True)
        return

    manager.dialog_data.update(
        {
            "task_id": str(selected.get("id")),
            "task_title": selected.get("title", "Без названия"),
        }
    )
    await manager.switch_to(DeleteTaskSG.confirm)


async def confirm_delete(
        callback: CallbackQuery,
        _: Button,
        manager: DialogManager,
) -> None:
    """
    Удаляет задачу и уведомляет пользователя о результатах.

    Args:
        callback (CallbackQuery): Объект колбека от пользователя.
        _: Кнопка, вызвавшая действие.
        manager (DialogManager): Менеджер диалога с данными.

    Raises:
        BackendError: Ошибка взаимодействия с бэкенд-сервисом.
        Exception: Любая другая непредвиденная ошибка.
    """

    task_id = manager.dialog_data.get("task_id")
    tg_id = callback.from_user.id

    if not task_id:
        await callback.answer("Не выбрана задача", show_alert=True)
        return

    api = BackendAPI()
    try:
        await api.delete_task(tg_id=tg_id, task_id=task_id)
    except BackendError as exc:
        message = str(exc)
        if message.startswith("404"):
            user_message = "Задача уже удалена или недоступна."
        else:
            user_message = f"Ошибка удаления: {message}"
        await callback.answer("Не удалось удалить", show_alert=True)
        await callback.message.answer(user_message)
        return
    except Exception as exc:  # pragma: no cover - страховка на непредвиденные ошибки
        await callback.answer("Не удалось удалить", show_alert=True)
        await callback.message.answer(f"Непредвиденная ошибка: {exc}")
        return
    finally:
        await api.aclose()

    await callback.message.answer(f"Задача #{task_id} успешно удалена.")
    await manager.done()


delete_task_dialog = Dialog(
    Window(
        Const("Выбери задачу для удаления:"),
        Format("{tasks_text}"),
        ScrollingGroup(
            Select(
                Format("{item[label]}"),
                id="delete_tasks_select",
                item_id_getter=lambda item: item["id"],
                items="tasks",
                on_click=on_task_selected,
            ),
            id="delete_tasks_scroll",
            width=1,
            height=8,
            when="has_tasks",
        ),
        Cancel(Const("Отмена")),
        state=DeleteTaskSG.choose_task,
        getter=tasks_getter,
    ),
    Window(
        Format("Удалить задачу #{dialog_data[task_id]} — {dialog_data[task_title]}?"),
        Button(Const("Удалить"), id="confirm_delete_btn", on_click=confirm_delete),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=DeleteTaskSG.confirm,
    ),
)

router = Router(name="delete_task")
