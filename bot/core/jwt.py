"""Создает краткосрочный RS256 JWT для сервисной авторизации бота."""

from __future__ import annotations

import time
from typing import Any

import jwt

from core.config import settings


def build_bot_jwt(extra_claims: dict[str, Any] | None = None) -> str:
    """
    Создает JWT токен для бота с заданными утверждениями.

    Args:
        extra_claims (dict[str, Any] | None): Дополнительные утверждения для включения в токен.

    Returns:
        str: Сгенерированный JWT токен.

    Raises:
        RuntimeError: Если возникла ошибка при создании токена.
    """
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": settings.bot_jwt_iss,
        "aud": settings.bot_jwt_aud,
        "iat": now,
        "nbf": now - 1,
        "exp": now + settings.bot_jwt_ttl,
        "scope": settings.bot_jwt_scope,
    }
    if extra_claims:
        claims.update(extra_claims)
    token = jwt.encode(claims, settings.bot_jwt_private_key, algorithm="RS256")
    return token
