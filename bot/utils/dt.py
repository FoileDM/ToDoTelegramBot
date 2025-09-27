"""Парсинг и форматирование даты/времени по пользовательскому часовому поясу."""

from __future__ import annotations

from datetime import datetime
from dateutil import tz

from core.config import settings


def parse_user_datetime(text: str) -> datetime:
    """
    Парсит строку с датой и временем, приводя её к объекту datetime в UTC.

    Args:
        text (str): Строка с датой и временем.

    Returns:
        datetime: Объект datetime с временем в UTC.

    Raises:
        ValueError: Если строка не соответствует ожидаемым форматам.
    """
    text = text.strip()
    local_tz = tz.gettz(settings.user_tz)
    for fmt in ("%d.%m.%Y %H:%M", "%Y-%m-%d %H:%M"):
        try:
            dt_naive = datetime.strptime(text, fmt)
            dt_local = dt_naive.replace(tzinfo=local_tz)
            return dt_local.astimezone(tz.UTC)
        except ValueError:
            continue
    raise ValueError("Неверный формат. Пример: 31.12.2025 14:30")


def format_dt_user(dt_iso: str | None) -> str:
    """
    Форматирует дату и время в строку в локальной временной зоне пользователя.

    Args:
        dt_iso (str | None): Дата и время в формате ISO 8601 или None.

    Returns:
        str: Форматированная строка с датой и временем или "-" при отсутствии входного значения.
    """
    if not dt_iso:
        return "-"
    local_tz = tz.gettz(settings.user_tz)
    dt = datetime.fromisoformat(dt_iso.replace("Z", "+00:00"))
    return dt.astimezone(local_tz).strftime("%d.%m.%Y %H:%M")
