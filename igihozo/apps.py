from django.apps import AppConfig


class IgihozoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "igihozo"

    def ready(self):
        from . import signals  # noqa: F401
