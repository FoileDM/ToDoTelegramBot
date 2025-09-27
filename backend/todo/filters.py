"""Модуль предоставляет функции для работы с категориями и задачами."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from todo.models import Category, Task

User = get_user_model()


def categories_for_list(user: User | None) -> QuerySet[Category]:
    """
    Возвращает отсортированный список категорий в зависимости от состояния пользователя.

    Args:
        user (User | None): Пользователь, для которого фильтруются категории. Может быть
            аутентифицированным или None.

    Returns:
        QuerySet[Category]: Запрос категорий, отсортированных по названию.
    """
    qs = Category.objects.all()
    if user and user.is_authenticated:
        qs = qs.filter(Q(owner__isnull=True) | Q(owner=user))
    else:
        qs = qs.filter(owner__isnull=True)
    return qs.order_by("name")


def tasks_for_user(user: User) -> QuerySet[Task]:
    """
    Возвращает список задач, связанных с указанным пользователем.

    Args:
        user (User): Пользователь, для которого нужно получить задачи.

    Returns:
        QuerySet[Task]: Отфильтрованный и упорядоченный список задач пользователя.
    """
    return (
        Task.objects.select_related("user")
        .prefetch_related("categories")
        .filter(user=user)
        .order_by("-created_at")
    )
