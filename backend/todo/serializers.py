"""Сериализатор для работы с todo."""

from __future__ import annotations

from typing import Iterable, Sequence

from django.db.models import Q
from rest_framework import serializers

from todo.models import Category, Task, TaskStatus


class CategorySerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Category.

    Сериализует данные модели Category, управляет созданием и обновлением объектов.

    Attributes:
        Meta.model (Model): Модель, используемая для сериализации.
        Meta.fields (tuple): Поля, включенные в сериализацию.
        Meta.read_only_fields (tuple): Поля, доступные только для чтения.
    """

    class Meta:
        """
        Настраивает метаданные для сериализатора.

        Определяет отображаемые и только для чтения поля для модели Category.

        Attributes:
            model (type): Модель, используемая для сериализации (Category).
            fields (tuple): Поля, включённые в сериализацию (id, name, slug).
            read_only_fields (tuple): Поля, доступные только для чтения (id, slug).
        """
        model = Category
        fields = ("id", "name", "slug")
        read_only_fields = ("id", "slug")

    def create(self, validated_data):
        """
        Создает новый объект категории с указанным владельцем.

        Args:
            validated_data (dict): Данные, прошедшие валидацию.

        Returns:
            Category: Созданный объект категории.
        """
        user = self.context["request"].user
        return Category.objects.create(owner=user, **validated_data)

    def update(self, instance: Category, validated_data):
        """
        Обновляет экземпляр модели Category с использованием проверенных данных.

        Args:
            instance (Category): Экземпляр модели, который требуется обновить.
            validated_data (dict): Проверенные данные для обновления.

        Returns:
            Category: Обновленный экземпляр модели Category.
        """
        validated_data.pop("owner", None)
        return super().update(instance, validated_data)


class TaskSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели задачи.

    Позволяет управлять отображением и обработкой данных модели `Task`, включая категории
    и статус задачи.

    Attributes:
        categories (serializers.ListField): Поле для ввода списка категорий по id.
        categories_detail (serializers.SerializerMethodField): Поле, предоставляющее
            детализированную информацию о категориях.
    """
    categories = serializers.ListField(
        child=serializers.CharField(max_length=26),
        allow_empty=True,
        required=False,
        write_only=True,
    )
    categories_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        """
        Метакласс для управления сериализацией модели Task.

        Обеспечивает указание сериализуемых полей, полей только для чтения и их конфигурацию.

        Attributes:
            model (type): Связанная модель Task.
            fields (tuple): Поля, подлежащие сериализации.
            read_only_fields (tuple): Поля, доступные только для чтения.
        """
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "created_at",
            "due_at",
            "status",
            "categories",
            "categories_detail",
        )
        read_only_fields = ("id", "created_at")

    def get_categories_detail(self, obj: Task):
        """
        Возвращает подробности категорий объекта Task.

        Args:
            obj (Task): Экземпляр задачи, для которого требуется получить категории.

        Returns:
            list: Список словарей с информацией о категориях. Каждый словарь содержит
            "id", "name" и "slug" категории.
        """
        cats = obj.categories.all()
        return [{"id": c.id, "name": c.name, "slug": c.slug} for c in cats]

    def _resolve_categories(
            self, ids: Iterable[str], *, user
    ) -> Sequence[Category]:
        """
        Разрешает категории по идентификаторам с учетом пользователя.

        Args:
            ids (Iterable[str]): Список строковых идентификаторов категорий.
            user: Пользователь, для которого фильтруются категории.

        Returns:
            Sequence[Category]: Список найденных категорий.

        Raises:
            serializers.ValidationError: Вызывается, если одна или несколько категорий
                не найдены или недоступны для пользователя.
        """
        ids = list(dict.fromkeys(ids))  # де-дуп
        if not ids:
            return []
        # доступны: глобальные (owner is null) + свои
        qs = Category.objects.filter(Q(owner__isnull=True) | Q(owner=user), id__in=ids)
        found = list(qs)
        if len(found) != len(ids):
            missing = set(ids) - {c.id for c in found}
            raise serializers.ValidationError(
                {"categories": [f"Unknown or forbidden category id: {m}" for m in sorted(missing)]}
            )
        return found

    def validate_status(self, value: str) -> str:
        """
        Проверяет, является ли статус допустимым.

        Args:
            value (str): Статус задачи для проверки.

        Returns:
            str: Введённый статус, если он допустим.

        Raises:
            serializers.ValidationError: Если статус недопустим.
        """
        if value not in TaskStatus.values:
            raise serializers.ValidationError("Invalid status.")
        return value

    def create(self, validated_data):
        """
        Создает новый объект задачи и связывает его с пользователем и категориями.

        Args:
            validated_data (dict): Данные для создания задачи, включая категории.

        Returns:
            Task: Созданный объект задачи.
        """
        user = self.context["request"].user
        ids = validated_data.pop("categories", [])
        categories = self._resolve_categories(ids, user=user)
        task = Task.objects.create(user=user, **validated_data)
        if categories:
            task.categories.set(categories)
        return task

    def update(self, instance: Task, validated_data):
        """
        Обновляет экземпляр задачи, включая категории, на основе проверенных данных.

        Args:
            instance (Task): Экземпляр задачи, который необходимо обновить.
            validated_data (dict): Проверенные данные для обновления.

        Returns:
            Task: Обновленный экземпляр задачи.
        """
        user = self.context["request"].user
        ids = validated_data.pop("categories", None)
        instance = super().update(instance, validated_data)
        if ids is not None:
            cats = self._resolve_categories(ids, user=user)
            instance.categories.set(cats)
        return instance
