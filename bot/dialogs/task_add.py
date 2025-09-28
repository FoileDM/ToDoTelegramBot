"""Модуль для управления процессом добавления задачи при помощи состояний и диалогов."""

from __future__ import annotations

from aiogram import Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, Window
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Back, Cancel, Next, Select, ScrollingGroup
from aiogram_dialog.widgets.text import Const, Format
from services.api import BackendAPI

from utils.dt import parse_user_datetime


class AddTaskSG(StatesGroup):
    """
    Класс для управления состояниями при добавлении задачи.

    Представляет группу состояний для последовательного ввода данных, необходимых для создания задачи.

    Attributes:
        title (State): Состояние для ввода названия задачи.
        description (State): Состояние для ввода описания задачи.
        due_at (State): Состояние для ввода даты завершения задачи.
        categories (State): Состояние для выбора категорий задачи.
        confirm (State): Состояние для подтверждения добавления задачи.
    """
    title = State()
    description = State()
    due_at = State()
    categories = State()
    confirm = State()


async def on_title_input(m: Message, widget: TextInput, manager: DialogManager, text: str):
    """
    Обрабатывает ввод заголовка задачи.

    Args:
        m (Message): Сообщение, содержащее данные ввода.
        widget (TextInput): Виджет ввода текста.
        manager (DialogManager): Менеджер диалога.
        text (str): Введенный текст заголовка задачи.
    """
    manager.dialog_data["title"] = text.strip()
    await manager.switch_to(AddTaskSG.description)


async def on_desc_input(m: Message, widget: TextInput, manager: DialogManager, text: str):
    """
    Обрабатывает ввод текста для описания задачи.

    Args:
        m (Message): Сообщение пользователя.
        widget (TextInput): Поле ввода текста.
        manager (DialogManager): Менеджер диалога.
        text (str): Введённый пользователем текст.
    """
    manager.dialog_data["description"] = text.strip()
    await manager.switch_to(AddTaskSG.due_at)


async def on_due_input(m: Message, widget: TextInput, manager: DialogManager, text: str):
    """
    Обрабатывает ввод даты и времени от пользователя, проверяет его корректность и обновляет данные диалога.

    Args:
        m (Message): Сообщение, полученное от пользователя.
        widget (TextInput): Виджет для взаимодействия с текстовым вводом.
        manager (DialogManager): Менеджер, управляющий состоянием диалога.
        text (str): Текст, введенный пользователем.

    Raises:
        ValueError: Если пользователь ввел некорректные данные даты и времени.

    Returns:
        None
    """
    text = text.strip()
    if text:
        try:
            due = parse_user_datetime(text)
            manager.dialog_data["due_at_iso"] = due.isoformat()
        except ValueError as e:
            await m.answer(str(e))
            return
    else:
        manager.dialog_data["due_at_iso"] = None
    await manager.switch_to(AddTaskSG.categories)


async def categories_getter(dialog_manager: DialogManager, **kwargs):
    """
    Получает категории и сохраняет данные в dialog_manager.

    Args:
        dialog_manager (DialogManager): Менеджер диалогов.
        **kwargs: Дополнительные параметры.

    Returns:
        dict: Словарь с ключами "cats" для списка категорий (имен и id)
        и "selected" для выбранных категорий.

    Raises:
        Исключения, связанные с обращением к BackendAPI.
    """
    api = BackendAPI()
    tg_id = dialog_manager.event.from_user.id
    try:
        cats = await api.list_categories(tg_id=tg_id)  # [{id, name}, ...]
        dialog_manager.dialog_data["cats_all"] = cats  # сохраним «сырые» из API

        selected = set(dialog_manager.dialog_data.get("cats_sel", []))

        items = []
        for c in cats:
            cid = c["id"]
            items.append({
                "id": cid,
                "label": c["name"],
                "check": "✅" if cid in selected else "☐",
            })

        sel_names = [c["name"] for c in cats if c["id"] in selected]
        return {
            "cats": items,                            # для Select
            "selected": list(selected),               # если где-то нужно
            "sel_count": len(selected),               # для хедера
            "sel_list": ", ".join(sel_names) or "—",  # для хедера
        }
    finally:
        await api.aclose()


async def on_cat_select(c: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """
    Обрабатывает выбор категории пользователем, добавляя или удаляя элемент из выбранного.

    Args:
        c (CallbackQuery): Объект обратного вызова для обработки событий.
        widget (Select): Виджет выбора категорий.
        manager (DialogManager): Менеджер диалога для отслеживания состояния.
        item_id (str): Идентификатор выбранного элемента.
    """
    sel = set(manager.dialog_data.get("cats_sel", []))
    if item_id in sel:
        sel.remove(item_id)
    else:
        if len(sel) >= 3:
            try:
                await c.answer("Можно выбрать не более 3 тегов.", show_alert=True)
            except Exception:
                pass
            return
        sel.add(item_id)
    manager.dialog_data["cats_sel"] = list(sel)


async def finalize_creation(c: CallbackQuery, widget: Button, manager: DialogManager):
    """
    Завершает процесс создания задачи с использованием информации из текущего диалога.

    Args:
        c (CallbackQuery): Объект callback-запроса от Telegram.
        widget (Button): Виджет кнопки, вызвавшей обработчик.
        manager (DialogManager): Менеджер текущего диалога.
    """
    tg_id = manager.event.from_user.id
    title = manager.dialog_data.get("title")
    description = manager.dialog_data.get("description", "")
    due_at_iso = manager.dialog_data.get("due_at_iso")
    categories = manager.dialog_data.get("cats_sel", [])

    if len(categories) > 3:
        await c.answer("Нельзя больше 3 тегов. Уберите лишние.", show_alert=True)
        return

    api = BackendAPI()
    try:
        created = await api.create_task(
            tg_id=tg_id, title=title, description=description, due_at_iso=due_at_iso, categories=categories
        )
        await c.message.answer(f"Задача создана: {created.get('title')}")
    except Exception as e:
        await c.message.answer(f"Ошибка создания: {e}")
    finally:
        await api.aclose()
    await manager.done()


async def skip_desc(c: CallbackQuery, widget: Button, manager: DialogManager):
    """
    Очищает описание задачи и переключает диалог на шаг ввода срока выполнения.

    Args:
        c (CallbackQuery): Объект запроса обратного вызова.
        widget (Button): Кнопка, вызвавшая действие.
        manager (DialogManager): Менеджер диалога.
    """
    manager.dialog_data["description"] = ""
    await manager.switch_to(AddTaskSG.due_at)


async def skip_due(c: CallbackQuery, widget: Button, manager: DialogManager):
    """
    Сбрасывает значение даты выполнения задачи и переключает диалог на выбор категории.

    Args:
        c (CallbackQuery): Запрос из интерфейса Telegram.
        widget (Button): Кнопка, вызвавшая данный обработчик.
        manager (DialogManager): Менеджер диалога для управления состояниями и данными.
    """
    manager.dialog_data["due_at_iso"] = None
    await manager.switch_to(AddTaskSG.categories)


add_task_dialog = Dialog(
    Window(
        Const("Название задачи:"),
        TextInput(id="title_input", on_success=on_title_input),
        Cancel(Const("Отмена")),
        state=AddTaskSG.title,
    ),
    Window(
        Const("Описание (или оставь пустым):"),
        TextInput(id="desc_input", on_success=on_desc_input),
        Button(Const("Пропустить"), id="skip_desc", on_click=skip_desc),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=AddTaskSG.description,
    ),
    Window(
        Const("Дедлайн (формат 31.12.2025 14:30) — можно пропустить:"),
        TextInput(id="due_input", on_success=on_due_input),
        Button(Const("Пропустить"), id="skip_due", on_click=skip_due),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=AddTaskSG.due_at,
    ),
    Window(
        Const("Выбери категории (тапать по пунктам):"),
        Format("Выбрано: {sel_count}/3"),
        Format("Теги: {sel_list}"),
        ScrollingGroup(
            Select(
                Format("{item[check]} {item[label]}"),
                id="cats_select",
                item_id_getter=lambda x: x["id"],
                items="cats",
                on_click=on_cat_select,
            ),
            id="cats_scroll",
            width=1, height=6,
        ),
        Next(Const("Далее")),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        getter=categories_getter,
        state=AddTaskSG.categories,
    ),
    Window(
        Const("Создаём задачу?"),
        Button(Const("Создать"), id="create_btn", on_click=finalize_creation),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=AddTaskSG.confirm,
    ),
)

router = Router(name="add_task")
