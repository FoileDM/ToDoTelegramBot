"""Модуль для управления предустановленными глобальными категориями при миграции."""

from __future__ import annotations

from django.db.models.signals import post_migrate
from django.dispatch import receiver

PRESET_CATEGORIES: list[str] = [
    "Дом",
    "Работа",
    "Личное",
    "Здоровье",
]


@receiver(post_migrate)
def ensure_preset_categories(sender, **kwargs) -> None:
    """
    Обеспечивает наличие предустановленных категорий для приложения "todo".

    Args:
        sender: Сигнализатор события post_migrate.
        **kwargs: Дополнительные параметры сигнала.

    """
    if getattr(sender, "name", None) != "todo":
        return

    from services.pk_keygen import generate_pk
    from todo.models import Category, slugify_unicode

    for raw_name in PRESET_CATEGORIES:
        name = (raw_name or "").strip()
        if not name:
            continue
        slug = slugify_unicode(name)
        obj, created = Category.objects.get_or_create(
            owner=None,
            slug=slug,
            defaults={"id": generate_pk("C"), "name": name},
        )
        if not created and obj.name != name:
            obj.name = name
            obj.save(update_fields=["name"])
