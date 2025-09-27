"""Предоставляет доступ для чтения всем пользователям и разрешает изменение только владельцу объекта."""

from __future__ import annotations

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    Разрешает доступ только владельцу объекта или доступ только для чтения.

    Ограничивает запись только для владельца объекта, остальные могут только читать. Предназначен для использования
    в системе контроля доступа на уровне объектов.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        """
        Проверяет права доступа пользователя к объекту.

        Args:
            request: HTTP-запрос пользователя.
            view: Представление, связанное с запросом.
            obj: Объект, для которого проверяются права доступа.

        Returns:
            bool: True, если пользователь имеет доступ к объекту, иначе False.
        """
        if request.method in SAFE_METHODS:
            return True
        owner = getattr(obj, "owner", None)
        if owner is None:
            return False
        return owner == request.user


class IsTaskOwner(BasePermission):
    """
    Проверяет, является ли пользователь владельцем заданного объекта.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        """
        Проверяет, имеет ли пользователь доступ к объекту.

        Args:
            request: Запрос пользователя.
            view: Текущий объект представления.
            obj: Объект, доступ к которому проверяется.

        Returns:
            bool: Возвращает True, если пользователь объекта совпадает с пользователем,
            отправившим запрос, иначе False.
        """
        return getattr(obj, "user", None) == request.user
