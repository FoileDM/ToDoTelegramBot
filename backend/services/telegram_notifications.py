"""Utilities for sending Telegram notifications via the Bot API."""

from __future__ import annotations

import hashlib
import logging
from functools import lru_cache
from typing import Any, Final

import httpx
from celery import shared_task
from celery.app.task import Task
from celery.result import AsyncResult
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_CONNECT_TIMEOUT_SECONDS: Final[float] = 3.0
DEFAULT_READ_TIMEOUT_SECONDS: Final[float] = 8.0
DEFAULT_WRITE_TIMEOUT_SECONDS: Final[float] = 8.0
DEFAULT_POOL_TIMEOUT_SECONDS: Final[float] = 3.0
MAX_RETRIES: Final[int] = 5
BASE_RETRY_DELAY_SECONDS: Final[int] = 5
MAX_RETRY_DELAY_SECONDS: Final[int] = 60


class TelegramNotificationError(RuntimeError):
    """
    Исключение для ошибок отправки уведомлений в Telegram.
    """


class TelegramNotificationClient:
    """
    Клиент для отправки уведомлений через Telegram.

    Используется для взаимодействия с Telegram Bot API для отправки сообщений.

    Attributes:
        token (str): Токен бота, используемый для аутентификации.
        api_base_url (str): Базовый URL для Telegram API.
        timeout (httpx.Timeout): Настраиваемый таймаут для запросов.
    """

    def __init__(self, token: str, api_base_url: str, timeout: httpx.Timeout | None = None) -> None:
        """
        Инициализирует экземпляр класса с заданным токеном, базовым URL API и тайм-аутом.

        Args:
            token (str): Токен Telegram-бота.
            api_base_url (str): Базовый URL API.
            timeout (httpx.Timeout | None): Тайм-аут для HTTP-запросов.
                Если не указан, будут использованы значения по умолчанию.

        Raises:
            ValueError: Если токен Telegram-бота не предоставлен.
        """
        if not token:
            raise ValueError("Telegram bot token must be provided for notifications.")
        self._token: Final[str] = token
        self._api_base_url: Final[str] = api_base_url.rstrip("/")
        self._timeout: httpx.Timeout = timeout or httpx.Timeout(
            connect=DEFAULT_CONNECT_TIMEOUT_SECONDS,
            read=DEFAULT_READ_TIMEOUT_SECONDS,
            write=DEFAULT_WRITE_TIMEOUT_SECONDS,
            pool=DEFAULT_POOL_TIMEOUT_SECONDS,
        )
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        self._token_fingerprint: Final[str] = token_hash[:12]

    def send_message(
        self,
        chat_id: int,
        text: str,
        *,
        parse_mode: str | None = None,
        disable_web_page_preview: bool | None = None,
    ) -> dict[str, Any]:
        """
        Отправляет сообщение в заданный чат через Telegram API.

        Args:
            chat_id (int): Идентификатор чата, в который будет отправлено сообщение.
            text (str): Текст сообщения.
            parse_mode (str | None): Форматирование текста (например, Markdown или HTML). Необязательный параметр.
            disable_web_page_preview (bool | None): Отключает предпросмотр ссылок. Необязательный параметр.

        Returns:
            dict[str, Any]: Ответ API Telegram в формате словаря.

        Raises:
            TelegramNotificationError: Ошибка при взаимодействии с Telegram API.
            httpx.TimeoutException: Превышено время ожидания запроса.
            httpx.RequestError: Ошибка транспортного уровня при выполнении запроса.
            httpx.HTTPStatusError: Неожиданный HTTP-код статуса API Telegram.
        """
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if disable_web_page_preview is not None:
            payload["disable_web_page_preview"] = disable_web_page_preview

        endpoint = f"{self._api_base_url}/bot{self._token}/sendMessage"
        try:
            response = httpx.post(endpoint, json=payload, timeout=self._timeout)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning(
                "Timeout while sending Telegram message (bot_fingerprint=%s, chat_id=%s): %s",
                self._token_fingerprint,
                chat_id,
                exc,
            )
            raise
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Unexpected HTTP status from Telegram (bot_fingerprint=%s, status=%s): %s",
                self._token_fingerprint,
                exc.response.status_code,
                exc.response.text,
            )
            raise TelegramNotificationError(
                f"Telegram API returned HTTP {exc.response.status_code} while sending a message."
            ) from exc
        except httpx.RequestError as exc:
            logger.warning(
                "Transport error while contacting Telegram (bot_fingerprint=%s, chat_id=%s): %s",
                self._token_fingerprint,
                chat_id,
                exc,
            )
            raise

        try:
            response_data: dict[str, Any] = response.json()
        except ValueError as exc:
            logger.error(
                "Telegram API returned invalid JSON (bot_fingerprint=%s, chat_id=%s)",
                self._token_fingerprint,
                chat_id,
            )
            raise TelegramNotificationError("Telegram API returned an invalid response payload.") from exc
        if not response_data.get("ok", False):
            logger.error(
                "Telegram API returned an error (bot_fingerprint=%s, chat_id=%s, description=%s)",
                self._token_fingerprint,
                chat_id,
                response_data.get("description", "<no description>"),
            )
            raise TelegramNotificationError("Telegram API reported an unsuccessful operation.")
        return response_data


@lru_cache(maxsize=1)
def get_notification_client() -> TelegramNotificationClient:
    """
    Создает и возвращает экземпляр TelegramNotificationClient с заданной конфигурацией.

    Returns:
        TelegramNotificationClient: Клиент для отправки уведомлений через Telegram.
    """
    return TelegramNotificationClient(
        token=settings.TELEGRAM_BOT_TOKEN,
        api_base_url=settings.TELEGRAM_API_BASE,
    )


RETRYABLE_EXCEPTIONS: Final = (httpx.RequestError, TelegramNotificationError)


def _compute_retry_delay(retry_index: int) -> int:
    """
    Вычисляет задержку перед следующей попыткой с учетом экспоненциального роста.

    Args:
        retry_index (int): Индекс текущей попытки повторной операции.

    Returns:
        int: Задержка в секундах для следующей попытки.
    """
    delay = BASE_RETRY_DELAY_SECONDS * (2 ** retry_index)
    return min(delay, MAX_RETRY_DELAY_SECONDS)


@shared_task(bind=True, max_retries=MAX_RETRIES, name="services.telegram.send_message")
def send_telegram_message_task(
    self: Task,
    *,
    chat_id: int,
    text: str,
    parse_mode: str | None = None,
    disable_web_page_preview: bool | None = None,
) -> dict[str, Any]:
    """
    Отправляет сообщение в Telegram используя асинхронную задачу.

    Функция отправляет сообщение через Telegram клиент. При возникновении
    ошибок конфигурации или проблем с сетью возможно повторное выполнение
    задачи до указанного максимального числа попыток.

    Args:
        self (Task): Задача Celery.
        chat_id (int): Идентификатор чата, в который будет отправлено сообщение.
        text (str): Текст сообщения.
        parse_mode (str | None): Режим форматирования текста сообщения (опционально).
        disable_web_page_preview (bool | None): Флаг отключения предварительного
            просмотра ссылок в сообщении (опционально).

    Returns:
        dict[str, Any]: Ответ от Telegram API в виде словаря.

    Raises:
        RuntimeError: Если конфигурация клиента Telegram некорректна.
        self.retry: При ошибках сети или временных сбоях задача будет повторена.
    """
    try:
        client = get_notification_client()
    except ValueError as exc:
        logger.error("Telegram client configuration error: %s", exc)
        raise RuntimeError("Telegram notifications are not configured.") from exc

    try:
        return client.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
        )
    except RETRYABLE_EXCEPTIONS as exc:
        retry_count = self.request.retries
        countdown = _compute_retry_delay(retry_count)
        logger.warning(
            "Retrying Telegram notification (attempt=%s/%s, chat_id=%s): %s",
            retry_count + 1,
            MAX_RETRIES,
            chat_id,
            exc,
        )
        raise self.retry(exc=exc, countdown=countdown)


def send_task_due_message(telegram_chat_id: int, text: str) -> AsyncResult:
    """
    Отправляет сообщение о предстоящей задаче в указанный Telegram-чат.

    Args:
        telegram_chat_id (int): Идентификатор Telegram-чата, куда будет отправлено сообщение.
        text (str): Текст сообщения.

    Returns:
        AsyncResult: Объект, представляющий асинхронный результат выполнения задачи.
    """
    return send_telegram_message_task.delay(chat_id=telegram_chat_id, text=text)


def send_plaintext_notification(
    telegram_chat_id: int,
    text: str,
    *,
    parse_mode: str | None = None,
    disable_web_page_preview: bool = False,
) -> AsyncResult:
    """
    Отправляет текстовое уведомление через Telegram.

    Args:
        telegram_chat_id (int): Идентификатор чата Telegram.
        text (str): Текст сообщения.
        parse_mode (str | None): Опциональный режим форматирования текста.
        disable_web_page_preview (bool): Отключает предварительный просмотр веб-страниц, если установлено в True.

    Returns:
        AsyncResult: Объект асинхронного результата выполнения задачи.
    """
    return send_telegram_message_task.delay(
        chat_id=telegram_chat_id,
        text=text,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
    )


__all__ = [
    "TelegramNotificationClient",
    "TelegramNotificationError",
    "get_notification_client",
    "send_plaintext_notification",
    "send_task_due_message",
]