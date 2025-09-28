"""Модуль для управления процессом редактирования задач через диалоги."""

from __future__ import annotations

from typing import Any

from aiogram import Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Back, Button, Cancel, Next, ScrollingGroup, Select
from aiogram_dialog.widgets.text import Const, Format
from services.api import BackendAPI

from utils.dt import format_dt_user, parse_user_datetime


class EditTaskSG(StatesGroup):
    """
    Определяет группу состояний для редактирования задачи.

    Класс используется для управления процессом редактирования задачи поэтапно
    с помощью состояний.

    Attributes:
        choose_task (State): Состояние выбора задачи для редактирования.
        title (State): Состояние изменения названия задачи.
        description (State): Состояние изменения описания задачи.
        due_at (State): Состояние изменения срока завершения задачи.
        categories (State): Состояние изменения категорий задачи.
        confirm (State): Состояние подтверждения изменений.
    """
    choose_task = State()
    title = State()
    description = State()
    due_at = State()
    categories = State()
    confirm = State()


async def tasks_getter(dialog_manager: DialogManager, **kwargs: Any) -> dict[str, Any]:
    """
    Получает задачи пользователя с бэкенда и формирует данные для диалога.

    Args:
        dialog_manager (DialogManager): Управляет состоянием текущего диалога.
        **kwargs (Any): Дополнительные аргументы.

    Returns:
        dict[str, Any]: Данные, содержащие задачи, текстовое представление задач
        и информацию о наличии задач.

    Raises:
        None: Исключения не выбрасываются явно.
    """
    api = BackendAPI()
    tg_id = dialog_manager.event.from_user.id
    try:
        resp = await api.list_tasks(tg_id=tg_id, page=1)
        tasks: list[dict[str, Any]] = resp.get("results", [])
        dialog_manager.dialog_data["tasks_raw"] = tasks
        items: list[dict[str, str]] = []
        lines: list[str] = []
        for task in tasks:
            task_id = str(task.get("id"))
            title = task.get("title", "Без названия")
            items.append({
                "id": task_id,
                "label": f"#{task_id} — {title}",
            })
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
        widget: Select,
        manager: DialogManager,
        item_id: str,
) -> None:
    """
    Обрабатывает выбор задачи из списка и обновляет данные менеджера диалогов.

    Args:
        callback (CallbackQuery): Объект обратного вызова Telegram.
        widget (Select): Виджет выбора задачи в диалоге.
        manager (DialogManager): Менеджер диалогов для управления состояниями.
        item_id (str): Идентификатор выбранной задачи.

    Raises:
        ValueError: Если задача с указанным идентификатором не найдена.
    """
    tasks: list[dict[str, Any]] = manager.dialog_data.get("tasks_raw", [])
    selected = next((task for task in tasks if str(task.get("id")) == item_id), None)
    if selected is None:
        await callback.answer("Не удалось найти задачу", show_alert=True)
        return

    categories = selected.get("categories") or [
        str(cat.get("id")) for cat in selected.get("categories_detail", []) if cat.get("id")
    ]

    manager.dialog_data.update(
        {
            "task_id": str(selected.get("id")),
            "title": selected.get("title", ""),
            "description": selected.get("description", ""),
            "due_at_iso": selected.get("due_at"),
            "cats_sel": [str(cat_id) for cat_id in categories] if categories else [],
            "original": {
                "title": selected.get("title", ""),
                "description": selected.get("description", ""),
                "due_at": selected.get("due_at"),
                "categories": [str(cat_id) for cat_id in categories] if categories else [],
            },
        }
    )
    await manager.switch_to(EditTaskSG.title)


async def on_title_input(message: Message, widget: TextInput, manager: DialogManager, text: str) -> None:
    """
    Обрабатывает ввод названия задачи и обновляет данные диалога.

    Args:
        message (Message): Сообщение пользователя.
        widget (TextInput): Текстовый виджет для ввода данных.
        manager (DialogManager): Менеджер диалога.
        text (str): Введённый пользователем текст.

    Returns:
        None.

    Raises:
        ValueError: Если введённое название пустое.
    """
    new_title = text.strip()
    if not new_title:
        await message.answer("Название не может быть пустым. Нажми «Пропустить», чтобы оставить текущее.")
        return
    manager.dialog_data["title"] = new_title
    await manager.switch_to(EditTaskSG.description)


async def keep_title(_: CallbackQuery, __: Button, manager: DialogManager) -> None:
    """
    Сохраняет заголовок в данных диалога и переключает на этап редактирования описания.

    Args:
        _: CallbackQuery: Объект запроса обратного вызова.
        __: Button: Кнопка, отправившая запрос.
        manager: DialogManager: Менеджер диалога.

    Returns:
        None: Значение не возвращается.

    Raises:
        Ничего не выбрасывает.
    """
    manager.dialog_data["title"] = manager.dialog_data.get("original", {}).get("title", "")
    await manager.switch_to(EditTaskSG.description)


async def on_description_input(
        message: Message,
        widget: TextInput,
        manager: DialogManager,
        text: str,
) -> None:
    """
    Обрабатывает ввод текста описания, сохраняет его и переключает диалог на следующий этап.

    Args:
        message (Message): Сообщение, инициировавшее действие.
        widget (TextInput): Виджет, связанный с вводом текста.
        manager (DialogManager): Менеджер диалога, управляющий состоянием.
        text (str): Введенный пользователем текст.

    """
    manager.dialog_data["description"] = text.strip()
    await manager.switch_to(EditTaskSG.due_at)


async def keep_description(_: CallbackQuery, __: Button, manager: DialogManager) -> None:
    """
    Сохраняет описание задачи и переключает состояние диалога.

    Args:
        _: CallbackQuery: Ответ на нажатие кнопки.
        __: Button: Кнопка, вызвавшая событие.
        manager: DialogManager: Менеджер текущего диалога.

    """
    manager.dialog_data["description"] = manager.dialog_data.get("original", {}).get("description", "")
    await manager.switch_to(EditTaskSG.due_at)


async def clear_description(_: CallbackQuery, __: Button, manager: DialogManager) -> None:
    """
    Очищает описание задачи и переключает состояние диалога.

    Args:
        _: CallbackQuery: Объект обратного вызова Telegram.
        __: Button: Объект кнопки.
        manager: DialogManager: Менеджер состояния диалога.

    Returns:
        None
    """
    manager.dialog_data["description"] = ""
    await manager.switch_to(EditTaskSG.due_at)


async def on_due_input(message: Message, widget: TextInput, manager: DialogManager, text: str) -> None:
    """
    Обрабатывает ввод даты и времени от пользователя.

    Args:
        message (Message): Сообщение от пользователя.
        widget (TextInput): Виджет ввода текста.
        manager (DialogManager): Управляющий диалогами.
        text (str): Строка текста, введенная пользователем.

    Raises:
        ValueError: Если текст невозможно преобразовать в дату и время.
    """
    text = text.strip()
    if not text:
        manager.dialog_data["due_at_iso"] = manager.dialog_data.get("original", {}).get("due_at")
        await manager.switch_to(EditTaskSG.categories)
        return
    try:
        due_dt = parse_user_datetime(text)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    manager.dialog_data["due_at_iso"] = due_dt.isoformat()
    await manager.switch_to(EditTaskSG.categories)


async def keep_due(_: CallbackQuery, __: Button, manager: DialogManager) -> None:
    """
    Сохраняет исходную дату выполнения задачи и переключает диалог на выбор категорий.

    Args:
        _: CallbackQuery: Объект обратного вызова (не используется).
        __: Button: Кнопка (не используется).
        manager: DialogManager: Менеджер для управления состоянием диалога.

    Returns:
        None
    """
    manager.dialog_data["due_at_iso"] = manager.dialog_data.get("original", {}).get("due_at")
    await manager.switch_to(EditTaskSG.categories)


async def clear_due(_: CallbackQuery, __: Button, manager: DialogManager) -> None:
    """Удаляет сохраненное значение даты и времени и переключает состояние диалога.

    Args:
        _: CallbackQuery: Запрос обратного вызова.
        __: Button: Кнопка, вызвавшая действие.
        manager: DialogManager: Менеджер диалога.

    """
    manager.dialog_data["due_at_iso"] = None
    await manager.switch_to(EditTaskSG.categories)


async def categories_getter(dialog_manager: DialogManager, **kwargs: Any) -> dict[str, Any]:
    """Возвращает информацию о категориях и выбранных элементах.

    Args:
        dialog_manager (DialogManager): Объект менеджера диалога.
        **kwargs: Дополнительные аргументы.

    Returns:
        dict[str, Any]: Словарь с информацией о категориях, количестве выбранных
        категорий и их списке.

    Raises:
        Исключения, связанные с взаимодействием с BackendAPI.
    """
    api = BackendAPI()
    tg_id = dialog_manager.event.from_user.id
    try:
        cats = await api.list_categories(tg_id=tg_id)
        dialog_manager.dialog_data["cats_all"] = cats
        selected = set(str(cat_id) for cat_id in dialog_manager.dialog_data.get("cats_sel", []))
        items: list[dict[str, str]] = []
        for cat in cats:
            cat_id = str(cat["id"])
            is_selected = cat_id in selected
            items.append(
                {
                    "id": cat_id,
                    "label": cat["name"],
                    "check": "✅" if is_selected else "☐",
                }
            )
        selected_names = [cat["name"] for cat in cats if str(cat["id"]) in selected]
        return {
            "cats": items,
            "sel_count": len(selected),
            "sel_list": ", ".join(selected_names) or "—",
        }
    finally:
        await api.aclose()


async def on_category_toggle(
        callback: CallbackQuery,
        widget: Select,
        manager: DialogManager,
        item_id: str,
) -> None:
    """
    Обрабатывает переключение категории пользователем.

    Args:
        callback (CallbackQuery): Объект обратного вызова телеграм.
        widget (Select): Виджет выбора категории.
        manager (DialogManager): Менеджер диалога.
        item_id (str): Идентификатор выбранной категории.

    Raises:
        CallbackQuery.answer: Если количество выбранных категорий превышает 3.
    """
    selected = set(manager.dialog_data.get("cats_sel", []))
    if item_id in selected:
        selected.remove(item_id)
    else:
        if len(selected) >= 3:
            await callback.answer("Можно выбрать не более 3 категорий.", show_alert=True)
            return
        selected.add(item_id)
    manager.dialog_data["cats_sel"] = list(selected)


async def finalize_edit(callback: CallbackQuery, button: Button, manager: DialogManager) -> None:
    """
    Завершает редактирование задачи и сохраняет изменения.

    Args:
        callback (CallbackQuery): Объект обратного вызова от пользователя.
        button (Button): Нажатая кнопка интерфейса диалога.
        manager (DialogManager): Менеджер текущего диалога.

    Raises:
        Exception: Ошибка при обновлении задачи.
    """
    task_id = manager.dialog_data.get("task_id")
    if not task_id:
        await callback.answer("Задача не выбрана", show_alert=True)
        return
    original: dict[str, Any] = manager.dialog_data.get("original", {})
    title = manager.dialog_data.get("title", original.get("title", ""))
    description = manager.dialog_data.get("description", original.get("description", ""))
    due_at_iso = manager.dialog_data.get("due_at_iso", original.get("due_at"))
    categories_raw = manager.dialog_data.get("cats_sel", original.get("categories", []))
    new_categories = [str(cat_id) for cat_id in categories_raw]
    original_categories = [str(cat_id) for cat_id in original.get("categories", [])]

    payload: dict[str, Any] = {}
    if title != original.get("title"):
        payload["title"] = title
    if description != original.get("description"):
        payload["description"] = description
    if due_at_iso != original.get("due_at"):
        payload["due_at"] = due_at_iso
    if sorted(new_categories) != sorted(original_categories):
        payload["categories"] = new_categories

    if not payload:
        await callback.answer("Изменений нет", show_alert=True)
        await manager.done()
        return

    api = BackendAPI()
    tg_id = manager.event.from_user.id
    try:
        await api.patch_task(tg_id=tg_id, task_id=str(task_id), **payload)
        await callback.message.answer("Задача обновлена.")
    except Exception as exc:  # noqa: BLE001
        await callback.message.answer(f"Ошибка обновления: {exc}")
    finally:
        await api.aclose()
    await manager.done()


def build_summary(dialog_data: dict[str, Any]) -> str:
    """
    Создает текстовое резюме данных диалога.

    Args:
        dialog_data (dict[str, Any]): Данные, содержащие параметры диалога.

    Returns:
        str: Форматированное строковое представление данных о диалоге.
    """
    title = dialog_data.get("title", "—")
    description = dialog_data.get("description", "—") or "—"
    due_at_iso = dialog_data.get("due_at_iso")
    due_at = format_dt_user(due_at_iso) if due_at_iso else "—"
    cats_all = dialog_data.get("cats_all", [])
    cats_sel = {str(cat_id) for cat_id in dialog_data.get("cats_sel", [])}
    cats_names = [cat["name"] for cat in cats_all if str(cat["id"]) in cats_sel]
    cats_display = ", ".join(cats_names) if cats_names else "—"
    return (
        f"Название: {title}\n"
        f"Описание: {description}\n"
        f"Срок: {due_at}\n"
        f"Категории: {cats_display}"
    )


def due_hint(dialog_data: dict[str, Any]) -> str:
    """
    Генерирует текстовое представление даты завершения задачи в формате пользователя.

    Args:
        dialog_data (dict[str, Any]): Данные задачи, содержащие информацию о дате завершения.

    Returns:
        str: Дата завершения задачи в формате пользователя или сообщение "не задан",
        если дата отсутствует.
    """
    due_at_iso = dialog_data.get("due_at_iso") or dialog_data.get("original", {}).get("due_at")
    if due_at_iso:
        return format_dt_user(due_at_iso)
    return "не задан"


async def title_getter(dialog_manager: DialogManager, **kwargs: Any) -> dict[str, Any]:
    """
    Получает текущий заголовок из данных диалога.

    Args:
        dialog_manager (DialogManager): Менеджер диалога, содержащий данные диалога.
        **kwargs (Any): Дополнительные параметры.

    Returns:
        dict[str, Any]: Словарь с ключом "current_title", содержащим заголовок или дефолтное значение "—".
    """
    title = dialog_manager.dialog_data.get("title")
    if title:
        return {"current_title": title}
    original = dialog_manager.dialog_data.get("original", {})
    return {"current_title": original.get("title", "—") or "—"}


async def description_getter(dialog_manager: DialogManager, **kwargs: Any) -> dict[str, Any]:
    """
    Извлекает или формирует описание для текущего диалога.

    Args:
        dialog_manager (DialogManager): Менеджер текущего диалога.
        **kwargs: Дополнительные аргументы.

    Returns:
        dict[str, Any]: Словарь с текущим описанием.

    """
    description = dialog_manager.dialog_data.get("description")
    if description:
        return {"current_description": description}
    original = dialog_manager.dialog_data.get("original", {})
    original_description = original.get("description") or "—"
    return {"current_description": original_description}


async def due_getter(dialog_manager: DialogManager, **kwargs: Any) -> dict[str, Any]:
    """
    Возвращает текущий статус задолженности.

    Args:
        dialog_manager (DialogManager): Менеджер диалога, содержащий данные.
        **kwargs (Any): Дополнительные аргументы.

    Returns:
        dict[str, Any]: Словарь с текущим показателем задолженности.
    """
    return {"current_due": due_hint(dialog_manager.dialog_data)}


async def summary_getter(dialog_manager: DialogManager, **kwargs: Any) -> dict[str, Any]:
    """
    Получает сводную информацию from dialog_manager.

    Args:
        dialog_manager (DialogManager): Менеджер диалога, содержащий данные для анализа.
        **kwargs (Any): Дополнительные аргументы.

    Returns:
        dict[str, Any]: Словарь со сводной информацией.
    """
    return {"summary": build_summary(dialog_manager.dialog_data)}


edit_task_dialog = Dialog(
    Window(
        Const("Выбери задачу для редактирования:"),
        Format("{tasks_text}"),
        ScrollingGroup(
            Select(
                Format("{item[label]}"),
                id="tasks_select",
                item_id_getter=lambda item: item["id"],
                items="tasks",
                on_click=on_task_selected,
            ),
            id="tasks_scroll",
            width=1,
            height=8,
            when="has_tasks",
        ),
        Cancel(Const("Отмена")),
        state=EditTaskSG.choose_task,
        getter=tasks_getter,
    ),
    Window(
        Format("Текущее название: {current_title}"),
        Const("Введи новое название или нажми «Пропустить»."),
        TextInput(id="title_input", on_success=on_title_input),
        Button(Const("Пропустить"), id="skip_title", on_click=keep_title),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=EditTaskSG.title,
        getter=title_getter,
    ),
    Window(
        Format("Текущее описание: {current_description}"),
        Const("Введи новое описание, очисти или пропусти."),
        TextInput(id="desc_input", on_success=on_description_input),
        Button(Const("Пропустить"), id="skip_desc", on_click=keep_description),
        Button(Const("Очистить"), id="clear_desc", on_click=clear_description),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=EditTaskSG.description,
        getter=description_getter,
    ),
    Window(
        Format("Текущий срок: {current_due}"),
        Const("Введи новый срок (31.12.2025 14:30), пропусти или очисти."),
        TextInput(id="due_input", on_success=on_due_input),
        Button(Const("Пропустить"), id="skip_due", on_click=keep_due),
        Button(Const("Очистить"), id="clear_due", on_click=clear_due),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=EditTaskSG.due_at,
        getter=due_getter,
    ),
    Window(
        Const("Выбери категории (до 3 штук):"),
        Format("Выбрано: {sel_count}/3"),
        Format("Теги: {sel_list}"),
        ScrollingGroup(
            Select(
                Format("{item[check]} {item[label]}"),
                id="cats_select",
                item_id_getter=lambda item: item["id"],
                items="cats",
                on_click=on_category_toggle,
            ),
            id="cats_scroll",
            width=1,
            height=6,
        ),
        Next(Const("Далее")),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=EditTaskSG.categories,
        getter=categories_getter,
    ),
    Window(
        Const("Проверь изменения:"),
        Format("{summary}"),
        Button(Const("Сохранить"), id="save_task", on_click=finalize_edit),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=EditTaskSG.confirm,
        getter=summary_getter,
    ),
)

router = Router(name="edit_task")
