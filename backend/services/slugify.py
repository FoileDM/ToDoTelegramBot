"""Модуль для преобразования строк в удобный для URL формат с сохранением символов Unicode."""

import unicodedata

from django.utils.text import slugify


def slugify_unicode(value: str) -> str:
    """
    Преобразует строку в удобный для URL формат, сохраняя символы Unicode.

    Args:
        value (str): Исходная строка, которая будет преобразована.

    Returns:
        str: Строка, преобразованная в формат, пригодный для использования в URL.
    """
    value = unicodedata.normalize("NFKC", value)
    return slugify(value, allow_unicode=True)