"""Определяет маршруты URL для приложений Django."""

from __future__ import annotations

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from todo.views import CategoryViewSet, TaskViewSet, health

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"tasks", TaskViewSet, basename="task")

urlpatterns = [
    path("health/", health, name="health"),
    path("", include(router.urls)),
]
