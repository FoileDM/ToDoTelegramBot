"""Проверяет права доступа для аутентификации сервисов-ботов."""

from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsBotService(BasePermission):
    """
    Определяет права доступа для проверки аутентификации сервисов-ботов.

    Этот класс используется для ограничения доступа только для аутентифицированных
    сервисов-ботов. Проверяет, предоставлено ли правильное значение в поле "is_bot".

    Attributes:
        message (str): Сообщение для случаев, когда доступ запрещен.
    """
    message = "Bot service authentication required."

    def has_permission(self, request, view) -> bool:
        auth = getattr(request, "auth", None)
        if not isinstance(auth, dict):
            return False
        return bool(auth.get("is_bot"))
