"""Celery tasks for the todo application."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Final

from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.timezone import localtime

from services.telegram_notifications import send_plaintext_notification
from todo.models import Task, TaskStatus


LOGGER = logging.getLogger(__name__)
NOTIFICATION_LOOKAHEAD_HOURS: Final[int] = 24


@shared_task(name="todo.notify_upcoming_tasks")
def notify_upcoming_tasks() -> None:
    """
    Отправляет уведомления о приближающихся задачах пользователям через Telegram.

    Args:
        None

    Returns:
        None

    Raises:
        Exception: Если произошла ошибка при отправке уведомления Telegram.
    """
    now = timezone.now()
    notification_window_end = now + timedelta(hours=NOTIFICATION_LOOKAHEAD_HOURS)

    with transaction.atomic():
        tasks_to_notify = list(
            Task.objects.select_for_update(skip_locked=True)
            .select_related("user")
            .filter(
                status=TaskStatus.ACTIVE,
                due_at__isnull=False,
                due_notified_at__isnull=True,
                due_at__gt=now,
                due_at__lte=notification_window_end,
                user__telegram_user_id__isnull=False,
            )
        )

        processed_count = 0

        for task in tasks_to_notify:
            telegram_chat_id = task.user.telegram_user_id
            if telegram_chat_id is None:
                LOGGER.warning("Task %s has no Telegram chat ID despite filtering", task.pk)
                continue

            localized_due_at = localtime(task.due_at)
            due_at_display = date_format(localized_due_at, "DATETIME_FORMAT", use_l10n=True)
            message = f"{task.title}\n{due_at_display}"

            try:
                send_plaintext_notification(telegram_chat_id=telegram_chat_id, text=message)
            except Exception as exc:
                LOGGER.exception(
                    "Failed to send due notification for task %s: %s",
                    task.pk,
                    exc,
                )
                continue

            task.due_notified_at = timezone.now()
            task.save(update_fields=["due_notified_at"])
            processed_count += 1

    LOGGER.info("Processed %s upcoming task notifications", processed_count)


__all__ = ["notify_upcoming_tasks"]