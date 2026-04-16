from django.apps import AppConfig


class MucyoAimeMaximeConfig(AppConfig):
    name = 'mucyo_aime_maxime_app'
    verbose_name = 'UAS - User Authentication Service'
    
    def ready(self):
        """Initialize signals on app startup."""
        from . import signals  # Import signals to register receivers
        # Note: create_default_groups() moved to migrations or separate command
        # because it requires the database to be initialized.

