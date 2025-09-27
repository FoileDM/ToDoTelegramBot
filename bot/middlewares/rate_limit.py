""" Rate limit middleware"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


class RateLimitMiddleware(BaseMiddleware):
    """
    Ограничивает частоту выполнения обработчиков для пользователей.

    Ограничивает количество событий, которые пользователь может
    инициировать за указанный промежуток времени. Применяется для
    предотвращения спама или избыточных запросов к ботам.

    Attributes:
        limit (int): Максимальное количество запросов за указанный интервал времени.
        per (int): Интервал времени в секундах, на протяжении которого
            действует ограничение.
    """

    def __init__(self, limit: int = 5, per_seconds: int = 10):
        """
        Инициализирует объект с заданными ограничениями на количество вызовов.

        Args:
            limit (int): Максимальное количество вызовов за указанный период.
            per_seconds (int): Период времени в секундах, за который действует ограничение.
        """
        super().__init__()
        self.limit = limit
        self.per = per_seconds
        self._hits: dict[int, Deque[float]] = defaultdict(lambda: deque(maxlen=100))

    async def __call__(self, handler, event: TelegramObject, data: dict):
        """
        Обрабатывает события, ограничивая частоту обращений для каждого пользователя.

        Args:
            handler (Callable): Функция, обрабатывающая событие.
            event (TelegramObject): Объект события, например, Message или CallbackQuery.
            data (dict): Дополнительные данные, переданные обработчику.

        Returns:
            Any: Результат выполнения переданного обработчика.

        Raises:
            Exception: В случае если переданный обработчик или объект события вызовет ошибку.
        """
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        if user_id:
            now = time.time()
            dq = self._hits[user_id]
            while dq and now - dq[0] > self.per:
                dq.popleft()
            if len(dq) >= self.limit:
                if isinstance(event, Message):
                    await event.answer("Слишком часто. Попробуй чуть позже.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Слишком часто. Попробуй чуть позже.", show_alert=False)
            dq.append(now)
        return await handler(event, data)
