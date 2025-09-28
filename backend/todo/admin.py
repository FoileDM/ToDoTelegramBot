"""Admin configuration for Category and Task models."""

from django.contrib import admin

from todo.models import Category, Task


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Регистрирует и настраивает модель Category в административной панели Django.

    Подробное описание класса, его назначения и использования.

    Attributes:
        list_display (tuple): Поля модели, отображаемые в списочном виде.
        list_filter (tuple): Поля модели, доступные для фильтрации.
        search_fields (tuple): Поля модели, доступные для поиска.
        readonly_fields (tuple): Поля модели, доступные только для чтения.
        ordering (tuple): Поля, по которым будет выполняться сортировка записей.
    """

    list_display = ("id", "owner", "name", "slug")
    list_filter = ("owner",)
    search_fields = ("name", "slug")
    readonly_fields = ("id",)
    ordering = ("owner", "name")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """
    Регистрация модели Task в админ-панели и настройка её отображения.

    Класс настраивает представление и поведение модели Task в административной
    панели Django.

    Attributes:
        list_display (Iterable): Определяет, какие поля будут отображаться в
            списке записей.
        list_filter (Iterable): Указывает, какие поля использовать в фильтре.
        search_fields (Iterable): Определяет поля, которые можно использовать
            для поиска.
        readonly_fields (Iterable): Указывает поля, которые нельзя редактировать.
        ordering (Iterable): Устанавливает порядок отображения записей.
        filter_horizontal (Iterable): Указывает ManyToMany-поля для
            горизонтального фильтра.
    """

    list_display = ("id", "user", "title", "status", "created_at", "due_at")
    list_filter = ("status", "user", "created_at", "due_at")
    search_fields = ("title", "description")
    readonly_fields = ("id", "created_at")
    ordering = ("-created_at",)

    filter_horizontal = ("categories",)
