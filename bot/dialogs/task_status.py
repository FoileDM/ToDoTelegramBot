"""Диалог изменения статуса задач."""

from __future__ import annotations

from typing import Any

from aiogram import Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Back, Cancel, ScrollingGroup, Select
from aiogram_dialog.widgets.text import Const, Format

from services.api import BackendAPI, BackendError
from utils.fmt import STATUS_PRESENTATION


class ChangeTaskStatusSG(StatesGroup):
    """
    Определяет этапы состояния для изменения статуса задачи.

    Класс используется для управления состояниями в процессе выбора задачи и назначения
    ей нового статуса.

    Attributes:
        choose_task (State): Состояние выбора задачи.
        choose_status (State): Состояние выбора статуса.
    """
    choose_task = State()
    choose_status = State()


async def tasks_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    """
    Получает список задач для заданного пользователя.

    Args:
        dialog_manager (DialogManager): Менеджер диалога Telegram.
        **_ (Any): Дополнительные параметры.

    Returns:
        dict[str, Any]: Словарь с задачами, текстовым представлением задач и флагом наличия задач.

    Raises:
        Исключение: При ошибке запроса к API.
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
    Обрабатывает выбор задачи из списка.

    Ищет задачу с переданным идентификатором в списке задач и обновляет данные диалога.
    Переключает процесс диалога на выбор нового статуса задачи.

    Args:
        callback (CallbackQuery): Объект обратного вызова Telegram.
        _ (Select): Выбор элемента (не используется в текущем методе).
        manager (DialogManager): Менеджер диалогов для управления состояниями.
        item_id (str): Идентификатор выбранной задачи.

    Raises:
        CallbackAnswer: Возникает при отсутствии задачи с переданным идентификатором в списке.
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
            "current_status": selected.get("status"),
        }
    )
    await manager.switch_to(ChangeTaskStatusSG.choose_status)


async def statuses_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    """Получает и возвращает список статусов с соответствующими метками и текущим состоянием.

    Args:
        dialog_manager (DialogManager): Объект управления диалогом, содержащий данные
            о текущем состоянии.
        **_ (Any): Дополнительные аргументы.

    Returns:
        dict[str, Any]: Словарь с ключами "statuses" и "has_statuses". "statuses"
        содержит список статусов с идентификаторами и метками. "has_statuses"
        указывает наличие статусов (True, если они присутствуют, иначе False).
    """
    current_status = str(dialog_manager.dialog_data.get("current_status") or "")
    statuses: list[dict[str, str]] = []
    for status, (icon, label) in STATUS_PRESENTATION.items():
        suffix = " (текущий)" if status == current_status else ""
        statuses.append({"id": status, "label": f"{icon} {label}{suffix}"})
    return {"statuses": statuses, "has_statuses": bool(statuses)}


async def on_status_selected(
    callback: CallbackQuery,
    _: Select,
    manager: DialogManager,
    item_id: str,
) -> None:
    """
    Обрабатывает выбор нового статуса задачи.

    Если задача не выбрана или текущий статус совпадает с выбранным, выводит соответствующее уведомление.
    При успешном обновлении статуса, оповещает пользователя и завершает диалог.

    Args:
        callback (CallbackQuery): Объект с информацией о взаимодействии пользователя с кнопкой.
        _ (Select): Компонент с текущими данными выбора в диалоге.
        manager (DialogManager): Менеджер диалога для работы с данными текучего состояния.
        item_id (str): Идентификатор выбранного статуса.

    Raises:
        BackendError: Если обновление статуса не удалось из-за ошибки на сервере.
    """
    task_id = manager.dialog_data.get("task_id")
    task_title = manager.dialog_data.get("task_title", "Без названия")
    current_status = manager.dialog_data.get("current_status")
    if not task_id:
        await callback.answer("Не выбрана задача", show_alert=True)
        return
    if item_id == current_status:
        await callback.answer("Этот статус уже установлен", show_alert=True)
        return

    api = BackendAPI()
    tg_id = callback.from_user.id
    try:
        await api.patch_task(tg_id=tg_id, task_id=str(task_id), status=item_id)
    except BackendError as exc:
        await callback.answer("Не удалось обновить", show_alert=True)
        await callback.message.answer(f"Ошибка обновления статуса: {exc}")
        return
    finally:
        await api.aclose()

    manager.dialog_data["current_status"] = item_id
    icon, label = STATUS_PRESENTATION.get(item_id, ("⚪️", "Неизвестный статус"))
    await callback.answer()
    await callback.message.answer(
        f"Статус задачи #{task_id} — {task_title} обновлён на: {icon} {label}"
    )
    await manager.done()


change_task_status_dialog = Dialog(
    Window(
        Const("Выбери задачу для изменения статуса:"),
        Format("{tasks_text}"),
        ScrollingGroup(
            Select(
                Format("{item[label]}"),
                id="change_status_tasks_select",
                item_id_getter=lambda item: item["id"],
                items="tasks",
                on_click=on_task_selected,
            ),
            id="change_status_tasks_scroll",
            width=1,
            height=8,
            when="has_tasks",
        ),
        Cancel(Const("Отмена")),
        state=ChangeTaskStatusSG.choose_task,
        getter=tasks_getter,
    ),
    Window(
        Format(
            "Задача #{dialog_data[task_id]} — {dialog_data[task_title]}\n"
            "Выбери новый статус:"
        ),
        ScrollingGroup(
            Select(
                Format("{item[label]}"),
                id="status_select",
                item_id_getter=lambda item: item["id"],
                items="statuses",
                on_click=on_status_selected,
            ),
            id="status_scroll",
            width=1,
            height=8,
            when="has_statuses",
        ),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=ChangeTaskStatusSG.choose_status,
        getter=statuses_getter,
    ),
)

router = Router(name="change_task_status")