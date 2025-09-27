"""Сериализаторы для авторизации"""

from rest_framework import serializers


class BotRegisterSerializer(serializers.Serializer):
    """
    Сериализатор для регистрации бота.

    Этот класс используется для обработки данных, связанных с регистрацией бота.

    Attributes:
        tg_id (serializers.IntegerField): Telegram ID бота, должен быть целым числом не меньше 1.
        username (serializers.CharField): Имя пользователя бота, может быть пустым или null.
    """
    tg_id = serializers.IntegerField(min_value=1)
    username = serializers.CharField(allow_null=True, allow_blank=True, required=False)
