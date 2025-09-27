"""Users URLs."""

from __future__ import annotations

from django.urls import path

from users.views import BotRegisterView

urlpatterns = [
    path("register/", BotRegisterView.as_view(), name="bot-register"),
]
