"""Модуль для управления категориями, задачами и их статусами."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from services.pk_keygen import generate_pk
from services.slugify import slugify_unicode


class Category(models.Model):
    """
    Модель, представляющая категорию.

    Содержит информацию о категории, включая её идентификатор, владельца, имя и слаг.

    Attributes:
        id (str): Уникальный идентификатор категории.
        owner (User): Владелец категории, связанный с моделью пользователя.
        name (str): Имя категории.
        slug (str): Слаг категории.

    Метаданные:
        - Уникальное ограничение для комбинации поля `owner` и `slug`.
        - Индексация полей `owner` и `slug`.
    """
    id = models.CharField(primary_key=True, max_length=26, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "slug"], name="uq_category_owner_slug"),
        ]
        indexes = [
            models.Index(fields=["owner", "slug"]),
        ]

    def save(self, *args, **kwargs):
        """
        Сохраняет объект, генерируя уникальный идентификатор и слаг при необходимости.

        Args:
            *args: Дополнительные аргументы.
            **kwargs: Дополнительные именованные аргументы.
        """
        if not self.id:
            self.id = generate_pk("C")
        if not self.slug:
            self.slug = slugify_unicode(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class TaskStatus(models.TextChoices):
    """
    Перечисление возможных статусов задачи.

    Определяет категории статусов для задач в виде текстовых значений.

    Attributes:
        ACTIVE (str): Статус обозначает, что задача активна.
        DONE (str): Статус обозначает, что задача выполнена.
        EXPIRED (str): Статус обозначает, что задача истекла.
    """
    ACTIVE = "active", "Active"
    DONE = "done", "Done"
    EXPIRED = "expired", "Expired"


class Task(models.Model):
    """
    Класс для управления задачами.

    Представляет задачи, привязанные к пользователям, с детальной информацией о
    заголовке, описании, сроках выполнения, статусах и категориях.

    Атрибуты:
        id (str): Уникальный идентификатор задачи.
        user (ForeignKey): Пользователь, к которому привязана задача.
        title (str): Заголовок задачи.
        description (str): Описание задачи.
        created_at (datetime): Дата и время создания задачи.
        due_at (datetime): Дата и время выполнения задачи (опционально).
        status (str): Текущий статус задачи.
        categories (ManyToManyField): Категории, к которым относится задача.
    """
    id = models.CharField(primary_key=True, max_length=26, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=TaskStatus.choices, default=TaskStatus.ACTIVE)
    categories = models.ManyToManyField(Category, related_name="tasks", blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["due_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_pk("T")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"
