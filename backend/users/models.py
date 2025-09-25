"""Менеджер для управления пользовательской моделью User."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q

from services.pk_keygen import generate_pk


class UserManager(BaseUserManager):
    """
    Менеджер пользователей с методами создания обычных и суперпользователей.

    Используется для управления и создания экземпляров моделей User.
    """
    use_in_migrations = True

    def _create_user(self, username: str, password: str, **extra_fields: Any) -> "User":
        """
        Создает пользователя с заданным именем пользователя и паролем.

        Args:
            username (str): Имя пользователя.
            password (str | None): Пароль пользователя. Если None, для пользователя устанавливается
                неактивный пароль.
            **extra_fields (Any): Дополнительные параметры для создания пользователя.

        Returns:
            User: Созданный пользователь.

        Raises:
            ValueError: Если имя пользователя не указано.
        """
        if not username:
            raise ValueError("The given username must be set")
        user = self.model(username=username, password=password, **extra_fields)
        user.set_password(password)
        if not user.id:
            user.id = generate_pk("U")
        user.save(using=self._db)
        return user

    def create_user(self, username: str, password: str, **extra_fields: Any) -> "User":
        """
        Создает пользователя с указанными данными.

        Args:
            username (str): Имя пользователя.
            password (str): Пароль пользователя или None.
            **extra_fields (Any): Дополнительные поля для создания пользователя.

        Returns:
            User: Созданный пользователь.
        """
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username: str, password: str, **extra_fields: Any) -> "User":
        """
        Создает суперпользователя с заданными параметрами.

        Args:
            username (str): Имя пользователя.
            password (str): Пароль пользователя.
            **extra_fields (Any): Дополнительные поля для создания пользователя.

        Returns:
            User: Экземпляр созданного суперпользователя.

        Raises:
            ValueError: Если is_staff не установлен в True.
            ValueError: Если is_superuser не установлен в True.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(username, password, **extra_fields)

    def create_from_telegram(self, tg_user_id: int) -> "User":
        """
        Создает или извлекает существующего пользователя на основе Telegram ID.

        Args:
            tg_user_id (int): Идентификатор пользователя в Telegram.

        Returns:
            User: Пользователь, созданный или извлеченный из базы данных.
        """
        user, created = self.get_or_create(
            telegram_user_id=tg_user_id,
            defaults={"id": generate_pk("U"), "username": None},
        )
        return user


class User(AbstractBaseUser, PermissionsMixin):
    """
    Представляет модель пользователя с расширенными функциями.

    Модель для работы с пользователями, включающая уникальный идентификатор, имя пользователя
    и опциональную связь с Telegram ID.

    Атрибуты:
        id (str): Уникальный первичный ключ пользователя.
        username (str): Уникальное имя пользователя.
        telegram_user_id (int|None): ID пользователя в Telegram, если указан.
        is_active (bool): Статус активности пользователя.
        is_staff (bool): Признак административных прав пользователя.
    """
    id = models.CharField(primary_key=True, max_length=26, editable=False)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    telegram_user_id = models.BigIntegerField(null=True, blank=True, unique=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        """
        Содержит метаинформацию и ограничения для модели.

        Определяет ограничение, требующее, чтобы хотя бы одно из полей
        'username' или 'telegram_user_id' было заполнено.

        Attributes:
            constraints (List[models.CheckConstraint]): Набор ограничений для модели.
        """
        constraints = [
            models.CheckConstraint(
                check=Q(username__isnull=False) | Q(telegram_user_id__isnull=False),
                name="user_username_or_tg_required",
            ),
        ]

    def save(self, *args, **kwargs):
        """
        Сохраняет объект, генерируя уникальный первичный ключ, если его нет.

        Args:
            *args: Дополнительные позиционные аргументы.
            **kwargs: Дополнительные именованные аргументы.
        """
        if not self.id:
            self.id = generate_pk("U")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.username or f"tg:{self.telegram_user_id}"
