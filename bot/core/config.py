"""Application configuration."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Хранит настройки приложения.

    Класс предназначен для хранения и управления конфигурацией приложения. Все параметры
    загружаются из переменных окружения или задаются с использованием значений по умолчанию.

    Attributes:
        bot_token (str): Токен Telegram-бота.
        backend_base_url (str): Базовый URL для Backend API.
        bot_jwt_private_key (str): Приватный ключ для генерации JWT.
        bot_jwt_iss (str): Значение поля "iss" для JWT.
        bot_jwt_aud (str): Значение поля "aud" для JWT.
        bot_jwt_scope (str): Значение поля "scope" для JWT.
        bot_jwt_ttl (int): Время жизни JWT в секундах. Значение по умолчанию: 120.
        http_timeout (float): Таймаут HTTP-запросов в секундах. Значение по умолчанию: 10.0.
        http_retries (int): Количество попыток повторить HTTP-запрос. Значение по умолчанию: 3.
        user_tz (str): Часовой пояс пользователя. Значение по умолчанию: "America/Adak".
        health_port (int): Порт для сервера проверки состояния приложения. Значение по умолчанию: 8000.
    """
    # Telegram
    bot_token: str = Field(alias="BOT_TOKEN")

    # Backend API
    backend_base_url: str = Field(alias="BACKEND_BASE_URL")

    # S2S JWT
    bot_jwt_private_key: str = Field(alias="BOT_JWT_PRIVATE_KEY")
    bot_jwt_iss: str = Field(alias="BOT_JWT_ISS")
    bot_jwt_aud: str = Field(alias="BOT_JWT_AUD")
    bot_jwt_scope: str = Field(alias="BOT_JWT_SCOPE")
    bot_jwt_ttl: int = Field(120, alias="BOT_JWT_TTL")  # seconds

    # HTTP
    http_timeout: float = Field(10.0, alias="HTTP_TIMEOUT")
    http_retries: int = Field(3, alias="HTTP_RETRIES")

    # UI
    user_tz: str = Field("America/Adak", alias="USER_TZ")

    # Health server
    health_port: int = Field(8000, alias="HEALTH_PORT")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
