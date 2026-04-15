from django.apps import AppConfig


class Uwase05Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'uwase05'

    def ready(self):
        # Register signal handlers for the profile model
        from . import signals  # noqa: F401
