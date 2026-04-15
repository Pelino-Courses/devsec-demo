from django.apps import AppConfig


class MucyoAimeMaximeConfig(AppConfig):
    name = 'mucyo_aime_maxime'
    verbose_name = 'UAS - User Authentication Service'
    
    def ready(self):
        """Initialize default groups on app startup."""
        from .admin import create_default_groups
        create_default_groups()
