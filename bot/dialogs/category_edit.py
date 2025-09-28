"""Диалоговое окно для переименования категорий."""

from __future__ import annotations

from typing import Any

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Back, Button, Cancel, ScrollingGroup, Select
from aiogram_dialog.widgets.text import Const, Format

from services.api import BackendAPI


class EditCategorySG(StatesGroup):
    """Группа состояний для сценария переименования категории."""

    choose_category = State()
    new_name = State()
    confirm = State()


async def categories_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    """Загружает список категорий пользователя для отображения в диалоге.

    Args:
        dialog_manager (DialogManager): Менеджер диалога, управляющий контекстом.
        **_ (Any): Дополнительные аргументы, которые игнорируются.

    Returns:
        dict[str, Any]: Данные для шаблонов диалога.
    """

    api = BackendAPI()
    tg_id = dialog_manager.event.from_user.id
    try:
        categories = await api.list_categories(tg_id=tg_id)
    finally:
        await api.aclose()

    items: list[dict[str, str]] = []
    for category in categories:
        identifier = category.get("id") or category.get("slug")
        name = category.get("name", "Без названия")
        if identifier is None:
            continue
        items.append(
            {
                "id": str(identifier),
                "label": f"{name}",
            }
        )

    dialog_manager.dialog_data["categories_raw"] = categories
    has_categories = bool(items)
    return {
        "categories": items,
        "has_categories": has_categories,
        "no_categories": not has_categories,
    }


async def on_category_selected(
    callback: CallbackQuery,
    _: Select,
    manager: DialogManager,
    item_id: str,
) -> None:
    """Обрабатывает выбор категории и запоминает исходные данные.

    Args:
        callback (CallbackQuery): Входящий колбэк от Telegram.
        _ (Select): Виджет выбора, породивший событие.
        manager (DialogManager): Менеджер диалога.
        item_id (str): Идентификатор выбранной категории.
    """

    categories: list[dict[str, Any]] = manager.dialog_data.get("categories_raw", [])
    selected = next(
        (
            category
            for category in categories
            if str(category.get("id")) == item_id
            or str(category.get("slug")) == item_id
        ),
        None,
    )
    if selected is None:
        await callback.answer("Категория не найдена", show_alert=True)
        return

    manager.dialog_data.update(
        {
            "category_id": str(selected.get("id") or selected.get("slug") or item_id),
            "original_name": selected.get("name", ""),
            "new_name": selected.get("name", ""),
        }
    )
    await manager.switch_to(EditCategorySG.new_name)


async def on_name_input(
    message: Message,
    _: TextInput,
    manager: DialogManager,
    text: str,
) -> None:
    """Сохраняет введённое название и переводит диалог к подтверждению.

    Args:
        message (Message): Сообщение пользователя с новым названием.
        _ (TextInput): Виджет ввода текста.
        manager (DialogManager): Менеджер диалога.
        text (str): Введённое пользователем значение.
    """

    new_name = text.strip()
    if not new_name:
        await message.answer("Название не может быть пустым.")
        return
    if len(new_name) > 50:
        await message.answer("Название должно быть короче 50 символов.")
        return

    manager.dialog_data["new_name"] = new_name
    await manager.switch_to(EditCategorySG.confirm)


async def save_category(
    callback: CallbackQuery,
    _: Button,
    manager: DialogManager,
) -> None:
    """Отправляет новое название категории на бэкенд.

    Args:
        callback (CallbackQuery): Колбэк, вызвавший действие.
        _ (Button): Кнопка подтверждения.
        manager (DialogManager): Менеджер диалога.
    """

    category_id = manager.dialog_data.get("category_id")
    new_name: str = manager.dialog_data.get("new_name", "").strip()
    original_name: str = manager.dialog_data.get("original_name", "").strip()
    if not category_id:
        await callback.answer("Не удалось определить категорию", show_alert=True)
        return
    if not new_name:
        await callback.answer("Введите название", show_alert=True)
        return
    if new_name == original_name:
        await callback.answer("Название не изменилось", show_alert=True)
        return

    api = BackendAPI()
    tg_id = callback.from_user.id
    try:
        updated = await api.patch_category(
            tg_id=tg_id, category_id=str(category_id), name=new_name
        )
        await callback.message.answer(
            "Категория обновлена:\n"
            f"• Было: {original_name or '—'}\n"
            f"• Стало: {updated.get('name', new_name)}"
        )
        await manager.done()
    except Exception as exc:  # noqa: BLE001 - транслируем пользователю текст ошибки
        await callback.answer("Не удалось обновить", show_alert=True)
        await callback.message.answer(f"Ошибка переименования: {exc}")
    finally:
        await api.aclose()


edit_category_dialog = Dialog(
    Window(
        Const("Выбери категорию для переименования:"),
        ScrollingGroup(
            Select(
                Format("{item[label]}"),
                id="category_select",
                item_id_getter=lambda item: item["id"],
                items="categories",
                on_click=on_category_selected,
            ),
            id="category_scroll",
            width=1,
            height=8,
            when="has_categories",
        ),
        Const("Категорий пока нет. Создай новую через /addcat.", when="no_categories"),
        Cancel(Const("Отмена")),
        state=EditCategorySG.choose_category,
        getter=categories_getter,
    ),
    Window(
        Format("Текущее название: {dialog_data[original_name]}"),
        Const("Введи новое название категории."),
        TextInput(id="category_name_input", on_success=on_name_input),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=EditCategorySG.new_name,
    ),
    Window(
        Const("Подтвердить изменение названия?"),
        Format("Было: {dialog_data[original_name]}"),
        Format("Станет: {dialog_data[new_name]}"),
        Button(Const("Сохранить"), id="save_category_btn", on_click=save_category),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=EditCategorySG.confirm,
    ),
)