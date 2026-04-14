from django.apps import AppConfig


class TresorConfig(AppConfig):
    name = 'tresor'

    def ready(self):
        import tresor.signals
