from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, Window
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Back, Cancel
from aiogram_dialog.widgets.text import Const, Format

from services.api import BackendAPI

router = Router(name="add_category")


class AddCategorySG(StatesGroup):
    name = State()
    confirm = State()


async def on_name_input(m: Message, widget: TextInput, manager: DialogManager, text: str):
    """Сохраняем имя категории и идём на подтверждение."""
    name = text.strip()
    if not name:
        await m.answer("Название не может быть пустым.")
        return
    if len(name) > 50:
        await m.answer("Слишком длинно. Максимум 50 символов.")
        return
    manager.dialog_data["cat_name"] = name
    await manager.switch_to(AddCategorySG.confirm)


async def create_category(c: CallbackQuery, widget: Button, manager: DialogManager):
    """Делает POST в бекенд и завершает диалог."""
    tg_id = manager.event.from_user.id
    name = manager.dialog_data.get("cat_name", "").strip()
    if not name:
        await c.answer("Введите название.", show_alert=True)
        return

    api = BackendAPI()
    try:
        created = await api.create_category(tg_id=tg_id, name=name)
        # ожидаем, что DRF отдаст slug read-only
        slug = created.get("slug", "—")
        await c.message.answer(f"Категория создана:\n• Название: {created.get('name')}\n• Slug: {slug}")
        await manager.done()
    except Exception as e:
        # DRF обычно шлёт {"name": ["already exists", ...]} или detail
        msg = str(e)
        try:
            data = getattr(e, "data", None) or getattr(e, "response", None)
            data = getattr(data, "json", None) and e.response.json()
        except Exception:
            data = None
        if isinstance(data, dict):
            if "name" in data and isinstance(data["name"], list):
                msg = "Ошибка: " + "; ".join(map(str, data["name"]))
            elif "detail" in data:
                msg = f"Ошибка: {data['detail']}"
        await c.message.answer(msg or "Ошибка создания категории.")
    finally:
        await api.aclose()


@router.message(Command("addcat"))
async def cmd_addcat(m: Message, dialog_manager: DialogManager):
    """Старт отдельного диалога добавления категории."""
    await dialog_manager.start(AddCategorySG.name, mode=StartMode.NORMAL)


add_category_dialog = Dialog(
    Window(
        Const("Введите название новой категории:"),
        TextInput(id="cat_name_input", on_success=on_name_input),
        Cancel(Const("Отмена")),
        state=AddCategorySG.name,
    ),
    Window(
        Const("Создать эту категорию?"),
        Format("Название: <b>{dialog_data[cat_name]}</b>"),
        Button(Const("Создать"), id="create_cat_btn", on_click=create_category),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=AddCategorySG.confirm,
    ),
)
