"""Содержит утилиты для форматирования задач и категорий для отображения в Telegram."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from textwrap import shorten
from typing import Any, TypeAlias

from utils.dt import format_dt_user

DESCRIPTION_SHORT_LENGTH = 160
TAG_DISPLAY_LIMIT = 5

STATUS_PRESENTATION: Mapping[str, tuple[str, str]] = {
    "active": ("🟡", "В работе"),
    "done": ("✅", "Готово"),
    "expired": ("⏰", "Просрочено"),
}

CategoryPayload: TypeAlias = Mapping[str, Any]
TaskPayload: TypeAlias = Mapping[str, Any]


def _resolve_status(status: str | None) -> tuple[str, str]:
    """
    Определяет и возвращает иконку и метку для заданного статуса.

    Args:
        status (str | None): Статус, для которого нужно определить иконку и метку.
            Если значение None, используется статус по умолчанию.

    Returns:
        tuple[str, str]: Кортеж, содержащий иконку и метку статуса.

    """
    default_icon, default_label = "⚪️", "Неизвестный статус"
    if not status:
        return default_icon, default_label
    return STATUS_PRESENTATION.get(status, (default_icon, default_label))


def _format_tags(categories: Sequence[CategoryPayload] | None) -> str:
    """
    Форматирует категории в строку с хэштегами.

    Аргументы:
        categories (Sequence[CategoryPayload] | None): Список категорий с данными для преобразования.

    Возвращает:
        str: Отформатированная строка с хэштегами или "—", если категории отсутствуют.
    """

    if not categories:
        return "—"

    normalized_tags: list[str] = []
    for category in categories:
        slug = str(category.get("slug") or "").strip()
        name = str(category.get("name") or "").strip()
        tag_value = slug or name
        if not tag_value:
            # Пропускаем пустые значения, чтобы не засорять вывод.
            continue
        normalized_tags.append(f"#{tag_value}")

    if not normalized_tags:
        return "—"

    if len(normalized_tags) <= TAG_DISPLAY_LIMIT:
        return ", ".join(normalized_tags)

    visible_tags = normalized_tags[:TAG_DISPLAY_LIMIT]
    hidden_count = len(normalized_tags) - TAG_DISPLAY_LIMIT
    return ", ".join(visible_tags + [f"+{hidden_count}"])


def fmt_task_line(task: TaskPayload) -> str:
    """
    Форматирует строку задачи для отображения.

    Args:
        task (TaskPayload): Объект задачи, содержащий данные для форматирования.

    Returns:
        str: Отформатированная строка с данными задачи.
    """

    status_raw = task.get("status")
    status_icon, status_label = _resolve_status(status_raw if isinstance(status_raw, str) else None)
    title = str(task.get("title") or "Без названия")
    description_raw = str(task.get("description") or "").strip()
    description = (
        shorten(description_raw, width=DESCRIPTION_SHORT_LENGTH, placeholder="…")
        if description_raw
        else ""
    )
    created_at = format_dt_user(task.get("created_at"))
    due_at = format_dt_user(task.get("due_at"))
    categories_raw = task.get("categories_detail")
    is_sequence = isinstance(categories_raw, Sequence) and not isinstance(categories_raw, (str, bytes))
    categories: Sequence[CategoryPayload] | None = categories_raw if is_sequence else None
    tags = _format_tags(categories)

    lines: list[str] = [f"{status_icon} {status_label}", f"Название: {title}"]
    if description:
        lines.append(f"Описание: {description}")
    lines.append(f"Создана: {created_at}")
    lines.append(f"Дедлайн: {due_at}")
    lines.append(f"Теги: {tags}")
    return "\n".join(lines)


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
