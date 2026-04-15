from django.apps import AppConfig


class Uwase05Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'uwase05'

    def ready(self):
        # Ensure role groups exist before signals use them
        from .authorization import ensure_role_groups
        ensure_role_groups()

        # Register signal handlers for the profile model
        from . import signals  # noqa: F401
