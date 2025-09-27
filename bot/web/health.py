"""Обеспечивает работу сервера с маршрутом для проверки состояния."""

from __future__ import annotations

from aiohttp import web


async def health(_request: web.Request) -> web.Response:
    """
    Возвращает JSON-ответ с состоянием здоровья.

    Args:
        _request (web.Request): Объект HTTP-запроса.

    Returns:
        web.Response: JSON-ответ с ключом "status" и значением "ok".
    """
    return web.json_response({"status": "ok"})


def make_app() -> web.Application:
    """
    Создает экземпляр веб-приложения с настройкой маршрутов.

    Возвращает веб-приложение с заранее настроенным маршрутом к методу проверки состояния.

    Returns:
        web.Application: Настроенное веб-приложение.
    """
    app = web.Application()
    app.router.add_get("/health", health)
    return app
