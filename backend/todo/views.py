"""Модуль для обработки представлений и запросов, связанных с категориями и задачами."""

from __future__ import annotations

from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response

from todo.filters import categories_for_list, tasks_for_user
from todo.models import Category, Task
from todo.permissions import IsOwnerOrReadOnly, IsTaskOwner
from todo.serializers import CategorySerializer, TaskSerializer


@api_view(["GET"])
def health(_request):
    """
    Проверяет состояние сервиса.

    Args:
        _request: HTTP-запрос.

    Returns:
        Response: Ответ с состоянием сервиса и временной зоной.
    """
    return Response({"status": "ok", "tz": "America/Adak"})


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Представление для управления категориями.

    Управляет процессами получения, создания, изменения и удаления категорий.
    Определяет доступные пользователю действия в зависимости от его прав.

    Attributes:
        serializer_class: Сериализатор для работы с данными категорий.
        permission_classes (list): Список классов для проверки прав доступа.
        lookup_field (str): Поле для поиска объекта в запросах.
        queryset: Базовый кверисет, необходимый для работы класса.
    """
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    lookup_field = "id"
    queryset = Category.objects.none()  # DRF требует атрибут, реальный QS в get_queryset

    def get_queryset(self):
        """
        Получает набор запросов для пользователя.

        Args:
            None.

        Returns:
            QuerySet: Набор категорий, доступных для пользователя.
        """
        return categories_for_list(self.request.user)

    def perform_create(self, serializer: CategorySerializer):
        """
        Создает новый объект, сохраняя данные из сериализатора.

        Args:
            serializer (CategorySerializer): Сериализатор, содержащий проверенные данные для сохранения.
        """
        serializer.save()


class TaskViewSet(viewsets.ModelViewSet):
    """
    Представление для работы с задачами.

    Предоставляет методы для создания, чтения, обновления и удаления задач,
    используя настройки доступа и сериализацию данных.

    Attributes:
        serializer_class (Serializer): Указывает класс сериализатора для обработки данных задач.
        permission_classes (list): Список классов, обеспечивающих контроль доступа к представлению.
        lookup_field (str): Поле, используемое для поиска объектов.
        queryset (QuerySet): Базовый пустой набор запросов для задач.
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsTaskOwner]
    lookup_field = "id"
    queryset = Task.objects.none()

    def get_queryset(self):
        """
        Возвращает набор задач для текущего пользователя.

        Args:
            Нет аргументов.

        Returns:
            QuerySet: Набор задач, относящихся к текущему пользователю.
        """
        return tasks_for_user(self.request.user)

    def perform_create(self, serializer: TaskSerializer):
        """
        Сохраняет экземпляр данных через сериализатор.

        Args:
            serializer (TaskSerializer): Сериализатор, используемый для сохранения данных.
        """
        serializer.save()
