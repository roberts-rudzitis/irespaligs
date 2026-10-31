from django.apps import AppConfig


class SubscriptionsConfig(AppConfig):
    name = "apps.subscriptions"

    def ready(self):
        from . import signals  # noqa: F401 – connects the "start trial on sign-up" signal
