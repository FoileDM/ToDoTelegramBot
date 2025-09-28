"""Диалоговое окно для удаления категорий."""

from __future__ import annotations

from typing import Any

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Back, Button, Cancel, ScrollingGroup, Select
from aiogram_dialog.widgets.text import Const, Format
from services.api import BackendAPI, BackendError


class DeleteCategorySG(StatesGroup):
    """Сценарий состояний для удаления категории."""

    choose_category = State()
    confirm = State()


async def categories_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    """Получает список категорий и преобразует их для использования в диалогах.

    Args:
        dialog_manager (DialogManager): Менеджер диалога.
        **_ (Any): Другие параметры.

    Returns:
        dict[str, Any]: Словарь с ключами "categories", "has_categories", "no_categories".
        "categories" содержит список категорий для отображения. "has_categories" — True,
        если категории существуют, иначе False. "no_categories" — True, если категории отсутствуют.
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
        items.append({"id": str(identifier), "label": name})

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
    """
    Обрабатывает выбор категории пользователем.

    Args:
        callback (CallbackQuery): Объект с данными обратного вызова.
        _ (Select): Объект выбора диалога.
        manager (DialogManager): Менеджер диалогов для управления состоянием.
        item_id (str): Идентификатор выбранной категории.

    Raises:
        None: Если категория не найдена.
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
            "category_name": selected.get("name", "Без названия"),
        }
    )
    await manager.switch_to(DeleteCategorySG.confirm)


async def confirm_delete(
        callback: CallbackQuery,
        _: Button,
        manager: DialogManager,
) -> None:
    """
    Подтверждает удаление категории и выполняет ее удаление.

    Args:
        callback (CallbackQuery): Запрос от пользователя на подтверждение действия.
        _: Button: Кнопка, инициировавшая действие.
        manager (DialogManager): Менеджер диалога для управления состояниями.

    Raises:
        BackendError: Если возникли ошибки при обращении к API.
        Exception: В случае непредвиденной ошибки во время выполнения.
    """
    category_id = manager.dialog_data.get("category_id")
    category_name: str = manager.dialog_data.get("category_name", "Без названия")
    if not category_id:
        await callback.answer("Не выбрана категория", show_alert=True)
        return

    api = BackendAPI()
    tg_id = callback.from_user.id
    try:
        await api.delete_category(tg_id=tg_id, category_id=str(category_id))
    except BackendError as exc:
        message = str(exc)
        if message.startswith("404"):
            user_message = "Категория уже удалена или недоступна."
        else:
            user_message = f"Ошибка удаления: {message}"
        await callback.answer("Не удалось удалить", show_alert=True)
        await callback.message.answer(user_message)
        return
    except Exception as exc:
        await callback.answer("Не удалось удалить", show_alert=True)
        await callback.message.answer(f"Непредвиденная ошибка: {exc}")
        return
    finally:
        await api.aclose()

    await callback.message.answer(
        "Категория удалена. Связанные задачи останутся без категории и будут отображаться как 'без категории'."
    )
    await manager.done()


delete_category_dialog = Dialog(
    Window(
        Const("Выбери категорию для удаления:"),
        ScrollingGroup(
            Select(
                Format("{item[label]}"),
                id="delete_category_select",
                item_id_getter=lambda item: item["id"],
                items="categories",
                on_click=on_category_selected,
            ),
            id="delete_category_scroll",
            width=1,
            height=8,
            when="has_categories",
        ),
        Const("Категорий пока нет. Создай новую через /addcat.", when="no_categories"),
        Cancel(Const("Отмена")),
        state=DeleteCategorySG.choose_category,
        getter=categories_getter,
    ),
    Window(
        Format("Удалить категорию «{dialog_data[category_name]}»?"),
        Const("Задачи, привязанные к категории, останутся без категории."),
        Button(
            Const("Удалить"), id="confirm_delete_category_btn", on_click=confirm_delete
        ),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=DeleteCategorySG.confirm,
    ),
)
