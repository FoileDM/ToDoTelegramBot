"""Модуль для взаимодействия с бэкенд-сервисом через HTTP запросы."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from core.config import settings
from core.jwt import build_bot_jwt


class BackendAPI:
    """
    Класс для взаимодействия с бэкенд API.

    Предоставляет методы для выполнения различных операций, таких как регистрация,
    работа с категориями и задачами.

    Атрибуты:
        _client (httpx.AsyncClient): HTTP клиент для выполнения запросов.
        _retries (int): Количество попыток повторных запросов в случае ошибок.
    """

    def __init__(self) -> None:
        """
        Инициализирует экземпляр класса.

        Создает асинхронный HTTP-клиент с указанной базовой URL, тайм-аутом и заголовками.
        """
        self._client = httpx.AsyncClient(
            base_url=settings.backend_base_url.rstrip("/"),
            timeout=settings.http_timeout,
            headers={"Content-Type": "application/json"},
        )
        self._retries = settings.http_retries

    async def aclose(self) -> None:
        """
        Закрывает клиентское соединение асинхронно.
        """
        await self._client.aclose()

    async def _request(self, method: str, path: str, *, tg_id: int | None, json: Any | None = None) -> httpx.Response:
        """
        Выполняет HTTP-запрос к серверу с поддержкой механизма повторных попыток.

        Args:
            method (str): HTTP-метод запроса (например, GET, POST).
            path (str): Путь запроса к серверу.
            tg_id (int | None): ID пользователя Telegram, если применимо.
            json (Any | None): Тело JSON-запроса, если требуется.

        Returns:
            httpx.Response: Ответ сервера.

        Raises:
            httpx.ConnectError: Ошибка подключения к серверу.
            httpx.ReadTimeout: Тайм-аут чтения ответа от сервера.
            httpx.WriteError: Ошибка записи запроса на сервер.
        """
        url = f"{path}"
        last_exc: Exception | None = None
        for attempt in range(1, self._retries + 2):
            try:
                headers = {"Authorization": f"Bearer {build_bot_jwt()}"}
                if tg_id is not None and not path.startswith("/bot/"):
                    headers["X-Act-As-User"] = str(tg_id)
                resp = await self._client.request(method, url, headers=headers, json=json)
                if resp.status_code >= 500 and attempt <= self._retries:
                    await asyncio.sleep(0.2 * attempt)
                    continue
                return resp
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteError) as e:
                last_exc = e
                if attempt <= self._retries:
                    await asyncio.sleep(0.2 * attempt)
                    continue
                raise
        assert last_exc
        raise last_exc

    async def register(self, *, tg_id: int, username: str | None) -> dict[str, Any]:
        """
        Регистрирует нового пользователя в системе.

        Асинхронно отправляет POST-запрос на сервер для регистрации
        пользователя с заданным идентификатором Telegram и именем
        пользователя. Принимает JSON-объект с данными для передачи.

        Args:
            tg_id (int): Идентификатор пользователя Telegram.
            username (str | None): Имя пользователя Telegram, может быть None.

        Returns:
            dict[str, Any]: Ответ от сервера в формате JSON.

        Raises:
            BackendError: Если регистрация завершилась ошибкой, возникает
            исключение с кодом и текстом ошибки от сервера.
        """
        resp = await self._request("POST", "/bot/register/", tg_id=None, json={"tg_id": tg_id, "username": username})
        if resp.status_code not in (200, 201):
            raise BackendError(f"register failed: {resp.status_code} {safe_text(resp)}")
        return resp.json()

    async def list_categories(self, *, tg_id: int) -> list[dict[str, Any]]:
        """
        Возвращает список категорий.

        Args:
            tg_id (int): Идентификатор Telegram-пользователя.

        Returns:
            list[dict[str, Any]]: Список категорий. В случае использования DRF paginator
            возвращается содержимое ключа `results`.

        Raises:
            HTTPException: В случае, если запрос завершился с ошибкой.
        """
        resp = await self._request("GET", "/categories/", tg_id=tg_id)
        _raise_for_client(resp)
        return resp.json().get("results", resp.json())  # router может вернуть list, но DRF paginator — dict

    async def create_category(self, *, tg_id: int, name: str) -> dict[str, Any]:
        """
        Создает новую категорию.

        Args:
            tg_id (int): Telegram ID пользователя.
            name (str): Название категории.

        Returns:
            dict[str, Any]: Ответ сервера в формате JSON.

        Raises:
            ClientError: Возникает при некорректном ответе клиента.
        """
        resp = await self._request("POST", "/categories/", tg_id=tg_id, json={"name": name})
        _raise_for_client(resp)
        return resp.json()

    async def list_tasks(self, *, tg_id: int, page: int = 1, status: str | None = None,
                         category: str | None = None) -> dict[str, Any]:
        """
        Получает список задач с возможностью фильтрации по странице, статусу и категории.

        Args:
            tg_id (int): Уникальный идентификатор пользователя.
            page (int): Номер страницы (по умолчанию 1).
            status (str | None): Фильтр по статусу задачи (опционально).
            category (str | None): Фильтр по категории задачи (опционально).

        Returns:
            dict[str, Any]: Объект JSON с данными о задачах.

        Raises:
            Исключение клиента: Возникает в случае, если запрос не был выполнен успешно.
        """
        params = []
        if page and page > 1:
            params.append(f"page={page}")
        if status:
            params.append(f"status={status}")
        if category:
            params.append(f"category={category}")
        path = "/tasks/"
        if params:
            path += "?" + "&".join(params)
        resp = await self._request("GET", path, tg_id=tg_id)
        _raise_for_client(resp)
        return resp.json()

    async def create_task(self, *, tg_id: int, title: str, description: str = "", due_at_iso: str | None = None,
                          categories: list[str] | None = None) -> dict[str, Any]:
        """Создает задачу с указанными параметрами.

        Args:
            tg_id (int): Идентификатор пользователя.
            title (str): Название задачи.
            description (str): Описание задачи. Значение по умолчанию - пустая строка.
            due_at_iso (str | None): Дата и время завершения задачи в формате ISO 8601.
                Если значение не указано, параметр не передается.
            categories (list[str] | None): Список категорий задачи. Если значение
                не указано, параметр не передается.

        Returns:
            dict[str, Any]: Ответ сервера с данными созданной задачи.

        Raises:
            Исключение клиента: При неправильном ответе от сервера.
        """
        payload = {"title": title, "description": description}
        if due_at_iso:
            payload["due_at"] = due_at_iso
        if categories:
            payload["categories"] = categories
        resp = await self._request("POST", "/tasks/", tg_id=tg_id, json=payload)
        _raise_for_client(resp)
        return resp.json()

    async def patch_task(self, *, tg_id: int, task_id: str, **fields: Any) -> dict[str, Any]:
        """
        Выполняет PATCH-запрос для обновления задачи.

        Args:
            tg_id (int): Идентификатор телеграм-аккаунта пользователя.
            task_id (str): Уникальный идентификатор задачи.
            **fields (Any): Поля для обновления задачи.

        Returns:
            dict[str, Any]: Ответ сервера в формате словаря.

        Raises:
            Исключение клиента: Если сервер возвращает ошибку.
        """
        resp = await self._request("PATCH", f"/tasks/{task_id}/", tg_id=tg_id, json=fields)
        _raise_for_client(resp)
        return resp.json()

    async def delete_task(self, *, tg_id: int, task_id: str) -> None:
        """
        Удаляет задачу по идентификатору.

        Args:
            tg_id (int): Идентификатор пользователя в Telegram.
            task_id (str): Уникальный идентификатор задачи.

        Returns:
            None: Функция ничего не возвращает.

        Raises:
            Исключение: Если сервер вернул ошибку в ответе.
        """
        resp = await self._request("DELETE", f"/tasks/{task_id}/", tg_id=tg_id)
        _raise_for_client(resp)
        return None


class BackendError(RuntimeError):
    """
    Представляет ошибку, возникающую в бэкенде.

    Используется для идентификации ошибок, происходящих в процессе работы
    с бэкендом. Наследуется от RuntimeError.
    """
    pass


def _raise_for_client(resp: httpx.Response) -> None:
    """
    Поднимает исключение для клиентской ошибки, если статус ответа не успешный.

    Args:
        resp (httpx.Response): HTTP-ответ, который необходимо проверить.

    Raises:
        BackendError: Ошибка сервера с указанием статуса и текста ответа.
    """
    if 200 <= resp.status_code < 300:
        return
    text = safe_text(resp)
    raise BackendError(f"{resp.status_code}: {text}")


def safe_text(resp: httpx.Response) -> str:
    """
    Возвращает текстовый контент из ответа HTTP.

    Если ответ содержит JSON-структуру, извлекает поле "detail" или возвращает
    преобразованное в строку содержимое JSON. В случае исключения возвращает
    первые 200 символов текстового содержимого ответа.

    Args:
        resp (httpx.Response): Объект ответа HTTP.

    Returns:
        str: Извлеченный текст из ответа.
    """
    try:
        data = resp.json()
        if isinstance(data, dict) and "detail" in data:
            return str(data["detail"])
        return str(data)
    except Exception:
        return resp.text[:200]
