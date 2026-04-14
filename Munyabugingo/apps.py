from django.apps import AppConfig


class MunyabugingoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Munyabugingo'

    def ready(self):
        import Munyabugingo.signals
