from django.apps import AppConfig


class AlphaConfig(AppConfig):
    name = 'alpha'

    def ready(self):
        import alpha.signals
