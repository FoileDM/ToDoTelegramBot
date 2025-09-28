
from __future__ import annotations

from typing import Iterable

from utils.dt import format_dt_user


def fmt_task_line(t: dict) -> str:
    """
    Форматирует строку задачи для отображения.

    Args:
        t (dict): Словарь-сущность задачи с данными.

    Returns:
        str: Отформатированная строка задачи.

    Raises:
        KeyError: Если в словаре отсутствует необходимый ключ.
    """
    cats = t.get("categories_detail") or []
    cats_txt = ", ".join("#" + c["slug"] for c in cats[:3]) if cats else "—"
    created = format_dt_user(t.get("created_at"))
    status = t.get("status", "active")
    title = t.get("title", "")
    task_id = t.get("id")
    task_id_display = f"#{task_id}" if task_id is not None else "#—"
    return f"• {task_id_display} [{status}] {title} (создана: {created}) | {cats_txt}"


def fmt_categories_list(cats: Iterable[dict]) -> str:
    """
    Форматирует список категорий.

    Args:
        cats (Iterable[dict]): Итерация словарей с категориями, где каждый словарь
            должен содержать ключи 'name' и 'slug'.

    Returns:
        str: Сформированная строка с перечислением категорий или сообщение
            "Нет категорий.", если список пуст.
    """
    lines = []
    for c in cats:
        lines.append(f"• {c['name']} (/{c['slug']})")
    return "\n".join(lines) if lines else "Нет категорий."