"""Модуль для обработки регистрации бота через Telegram."""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from services.permissions import IsBotService
from users.models import User
from users.serializers import BotRegisterSerializer


class BotRegisterView(APIView):
    """
    Обрабатывает регистрацию бота.

    Реализует логику для регистрации пользователя через Telegram ID с возможностью обновления
    поля имени пользователя, если оно указано и ранее не было заполнено.

    Attributes:
        permission_classes (list): Список классов, определяющих уровень доступа
            к этому представлению. В данном случае доступ ограничен услугами бота.

    Methods:
        post(self, request, *args, **kwargs): Обработка POST-запроса для регистрации пользователя.
    """
    permission_classes = [IsBotService]

    def post(self, request, *args: Any, **kwargs: Any):
        """
        Обрабатывает POST-запрос для регистрации пользователя через Telegram.

        Args:
            request (Request): Запрос с данными регистрации Telegram.
            *args: Дополнительные позиционные аргументы.
            **kwargs: Дополнительные именованные аргументы.

        Returns:
            Response: Ответ с ID пользователя, Telegram ID и флагом нового пользователя.

        Raises:
            ValidationError: Если данные запроса недействительны.
        """
        data = BotRegisterSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        tg_id = data.validated_data["tg_id"]
        username = data.validated_data.get("username")

        user = User.objects.filter(telegram_user_id=tg_id).first()
        is_new = False
        if not user:
            user = User.objects.create_from_telegram(tg_user_id=tg_id)
            if username and not user.username:
                user.username = username
                user.save(update_fields=["username"])
            is_new = True

        return Response(
            {"user_id": user.id, "tg_id": user.telegram_user_id, "is_new": is_new},
            status=status.HTTP_200_OK if not is_new else status.HTTP_201_CREATED,
        )
