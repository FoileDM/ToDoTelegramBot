"""Модуль для генерации уникальных ключей на основе base62 формата."""

from __future__ import annotations

import os
import threading
import time
from typing import Final

_BASE62_ALPHABET: Final[str] = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_BASE: Final[int] = len(_BASE62_ALPHABET)
_MAX_LEN: Final[int] = 26

_lock = threading.Lock()
_last_ms = 0
_counter = 0


def _b62_encode(num: int) -> str:
    """
    Кодирует число в строку в формате base62.

    Функция принимает неотрицательное целое число и возвращает его строковое
    представление в 62-ричной системе счисления.

    Args:
        num (int): Неотрицательное целое число для конвертации.

    Returns:
        str: Строка, представляющая число в формате base62.

    Raises:
        ValueError: Если num меньше 0.
    """
    if num < 0:
        raise ValueError("num must be >= 0")
    if num == 0:
        return _BASE62_ALPHABET[0]
    chars = []
    while num > 0:
        num, rem = divmod(num, _BASE)
        chars.append(_BASE62_ALPHABET[rem])
    chars.reverse()
    return "".join(chars)


def _now_ms() -> int:
    """
    Возвращает текущее время в миллисекундах.

    Returns:
        int: Текущее время в миллисекундах.
    """
    return int(time.time() * 1000)


def _env_prefix() -> str:
    """
    Возвращает строку-префикс из переменной окружения, фильтрованную по заданному набору символов.

    Args:
        нет аргументов.

    Returns:
        str: Обрезанный и отфильтрованный префикс, состоящий из первых трех символов строки,
        содержащейся в переменной окружения PK_PREFIX, или "ABC" по умолчанию.
    """
    raw = os.getenv("PK_PREFIX", "ABC").strip()
    filtered = "".join(ch for ch in raw if ch in _BASE62_ALPHABET)[:3]
    return filtered


def generate_pk(kind: str) -> str:
    """
    Генерирует уникальный ключ на основе переданного символа типа.

    Args:
        kind (str): Символ, определяющий тип ключа. Должен быть одним символом из алфавита base62.

    Returns:
        str: Сгенерированный уникальный ключ.

    Raises:
        ValueError: Если `kind` пустой или длина параметра не равна 1.
        ValueError: Если `kind` не является допустимым символом алфавита base62.
    """
    if not kind or len(kind) != 1:
        raise ValueError("kind must be exactly 1 char")
    if kind not in _BASE62_ALPHABET:
        raise ValueError("kind must be a base62 char")

    prefix = _env_prefix()

    with _lock:
        global _last_ms, _counter
        now_ms = _now_ms()
        if now_ms == _last_ms:
            _counter += 1
        else:
            _last_ms = now_ms
            _counter = 0
        ts62 = _b62_encode(now_ms)
        cnt62 = _b62_encode(_counter)

    key = f"{prefix}{kind}{ts62}{cnt62}"
    return key
