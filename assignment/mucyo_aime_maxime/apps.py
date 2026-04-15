from django.apps import AppConfig


class MucyoAimeMaximeConfig(AppConfig):
    name = 'mucyo_aime_maxime'
    verbose_name = 'UAS - User Authentication Service'
    
    def ready(self):
        """Initialize default groups and signals on app startup."""
        from .admin import create_default_groups
        from . import signals  # Import signals to register receivers
        create_default_groups()
