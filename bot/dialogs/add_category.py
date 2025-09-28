from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, Window
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Back, Cancel
from aiogram_dialog.widgets.text import Const, Format
from services.api import BackendAPI

router = Router(name="add_category")


class AddCategorySG(StatesGroup):
    """
    Состояния для добавления категории.

    Группа состояний, используемая для управления процессом добавления новой категории.

    Attributes:
        name (State): Состояние для ввода имени категории.
        confirm (State): Состояние для подтверждения добавления категории.
    """
    name = State()
    confirm = State()


async def on_name_input(m: Message, widget: TextInput, manager: DialogManager, text: str):
    """
    Обрабатывает ввод имени и выполняет валидацию.

    Args:
        m (Message): Сообщение пользователя.
        widget (TextInput): Виджет ввода текста.
        manager (DialogManager): Менеджер диалога.
        text (str): Введенный текст.

    Raises:
        None: Не выбрасывает исключений.
    """
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
    """
    Создает новую категорию на сервере с учетом данных из пользовательского интерфейса.

    Args:
        c (CallbackQuery): Объект обратного вызова Telegram API.
        widget (Button): Кнопка, связанная с текущим контекстом диалога.
        manager (DialogManager): Менеджер диалога, управляющий состоянием и данными.

    Raises:
        Exception: Общая ошибка, если запрос на создание категории вернул исключение.
    """
    tg_id = manager.event.from_user.id
    name = manager.dialog_data.get("cat_name", "").strip()
    if not name:
        await c.answer("Введите название.", show_alert=True)
        return

    api = BackendAPI()
    try:
        created = await api.create_category(tg_id=tg_id, name=name)
        slug = created.get("slug", "—")
        await c.message.answer(f"Категория создана:\n• Название: {created.get('name')}\n• Slug: {slug}")
        await manager.done()
    except Exception as e:
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
    """
    Обрабатывает команду "addcat" для начала диалога добавления категории.

    Args:
        m (Message): Сообщение, содержащее команду.
        dialog_manager (DialogManager): Менеджер для работы с состояниями диалога.
    """
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
        Format("Название: {dialog_data[cat_name]}"),
        Button(Const("Создать"), id="create_cat_btn", on_click=create_category),
        Back(Const("Назад")),
        Cancel(Const("Отмена")),
        state=AddCategorySG.confirm,
    ),
)
