"""Celery application instance for the Django project."""

from __future__ import annotations

import os

from celery import Celery
from celery.app.task import Task

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

celery_app: Celery = Celery("config")
celery_app.config_from_object("django.conf:settings", namespace="CELERY")
celery_app.autodiscover_tasks()


@celery_app.task(bind=True)
def debug_task(self: Task) -> None:
    """
    Выводит информацию о выполнении задачи.

    Args:
        self (Task): Текущая задача.
    """
    print(f"Request: {self.request!r}")


__all__ = ["celery_app"]