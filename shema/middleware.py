import logging
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import user_logged_in, user_login_failed
from django.dispatch import receiver

logger = logging.getLogger('security')

class SecurityAuditMiddleware(MiddlewareMixin):
    """
    Middleware to log security-sensitive events.
    """
    def process_request(self, request):
        # We can log access to specific paths if needed
        pass

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR')
    logger.info(f"SUCCESSFUL_LOGIN: User '{user.username}' logged in from IP {ip}")

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    ip = request.META.get('REMOTE_ADDR')
    username = credentials.get('username', 'unknown')
    logger.warning(f"FAILED_LOGIN: Attempt for user '{username}' from IP {ip}")
