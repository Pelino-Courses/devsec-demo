from django.apps import AppConfig


class MupenzFulgenceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mupenz_fulgence'
    verbose_name = 'User Authentication Service'

    def ready(self):
        # Connect signal handlers when the app is ready
        import mupenz_fulgence.signals  # noqa: F401
