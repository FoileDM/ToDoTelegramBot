"""Обеспечивает JWT-аутентификацию для бот-сервиса."""

from __future__ import annotations

from typing import Any

import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils.translation import gettext_lazy as _
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from users.models import User


class BotServiceJWTAuthentication(BaseAuthentication):
    """
    Обеспечивает JWT-аутентификацию для бот-сервисов.

    Описание:
    Этот класс реализует аутентификацию, основанную на JWT (JSON Web Token), и включает
    в себя проверку токена, предотвращение повторного воспроизведения токенов, проверку
    прав доступа, а также поддержку пути выдачи полномочий.

    Attributes:
        www_authenticate_realm (str): Имя области для заголовка аутентификации.
    """

    www_authenticate_realm = "api"

    def authenticate(self, request):
        """
        Выполняет аутентификацию запроса с использованием Bearer-токена.

        Args:
            request: HTTP-запрос, содержащий заголовок авторизации и, возможно, идентификацию пользователя.

        Returns:
            tuple: Возвращает кортеж из пользователя (AnonymousUser или User) и объекта auth_info.

        Raises:
            AuthenticationFailed: Если отсутствует заголовок авторизации, токен не соответствует формату Bearer,
            предоставлен некорректный токен, указан недостаточный scope или пользователь не найден.
        """
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != b"bearer":
            return None

        if len(auth) == 1:
            raise AuthenticationFailed(_("Invalid Authorization header. No credentials provided."))
        if len(auth) > 2:
            raise AuthenticationFailed(_("Invalid Authorization header. Token string should not contain spaces."))

        token = auth[1].decode("utf-8")
        claims = self._decode_and_validate(token)

        if not self._has_scope(claims, required=settings.BOT_JWT_SCOPE):
            raise AuthenticationFailed(_("Insufficient scope"))

        tg_id_hdr = request.headers.get("X-Act-As-User")
        tg_id_claim = claims.get("tg_id")
        act_as = tg_id_hdr or tg_id_claim

        auth_info = {"is_bot": True, "claims": claims}

        if act_as is None:
            return AnonymousUser(), auth_info

        try:
            tg_id_int = int(act_as)
        except (ValueError, TypeError):
            raise AuthenticationFailed(_("Invalid X-Act-As-User"))

        user = User.objects.filter(telegram_user_id=tg_id_int, is_active=True).first()
        if not user:
            raise AuthenticationFailed(_("Unknown user (call /api/bot/register/ first)"))
        return user, auth_info

    def _decode_and_validate(self, token: str) -> dict[str, Any]:
        """
        Декодирует и валидирует JWT-токен.

        Args:
            token (str): JWT-токен, который требуется декодировать и проверить.

        Returns:
            dict[str, Any]: Расшифрованные данные из токена.

        Raises:
            AuthenticationFailed: Если ключ BOT_JWT_PUBLIC_KEY не установлен,
                токен истек, либо недействителен.
        """
        pubkey = getattr(settings, "BOT_JWT_PUBLIC_KEY", "")
        if not pubkey:
            raise AuthenticationFailed(_("Server misconfiguration: BOT_JWT_PUBLIC_KEY is not set"))

        try:
            claims = jwt.decode(
                token,
                pubkey,
                algorithms=[settings.BOT_JWT_ALG],
                audience=settings.BOT_JWT_AUD,
                issuer=settings.BOT_JWT_ISS,
                leeway=settings.BOT_JWT_LEEWAY,
                options={"require": ["iss", "aud", "exp", "iat"]},
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed(_("Token expired"))
        except jwt.InvalidTokenError as e:
            raise AuthenticationFailed(_(f"Invalid token: {e}"))
        return claims

    @staticmethod
    def _has_scope(claims: dict[str, Any], *, required: str) -> bool:
        """
        Проверяет наличие указанной области действия (scope) в переданных данных утверждений.

        Args:
            claims (dict[str, Any]): Данные утверждений, содержащие информацию о доступах.
            required (str): Необходимая область действия (scope), которую нужно проверить.

        Returns:
            bool: True, если указанная область действия есть в утверждениях, иначе False.
        """
        scope = claims.get("scope")
        if not scope:
            return False
        if isinstance(scope, str):
            return required in scope.split()
        if isinstance(scope, (list, tuple, set)):
            return required in scope
        return False

    def authenticate_header(self, request) -> str:
        """
        Генерирует заголовок аутентификации.

        Args:
            request: Запрос, для которого требуется заголовок аутентификации.

        Returns:
            str: Заголовок аутентификации в формате 'Bearer realm="<realm>"'.
        """
        return f'Bearer realm="{self.www_authenticate_realm}"'
