"""App configuration."""

from django.apps import AppConfig


class TodoConfig(AppConfig):
    """
    Конфигурация приложения для раздела "todo".

    Описание класса, его назначения и использования.

    Attributes:
        default_auto_field (str): Тип поля автоинкремента для моделей по умолчанию.
        name (str): Имя приложения.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'todo'

    def ready(self) -> None:
        """
        Инициализирует готовность приложения.

        Импортирует сигналы при запуске приложения для обеспечения их регистрации.

        Returns:
            None: Ничего не возвращает.
        """
        from . import signals  # noqa: F401
