import logging
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import user_logged_in, user_login_failed, user_logged_out
from django.dispatch import receiver
from django.db.models.signals import m2m_changed
from django.contrib.auth.models import User

logger = logging.getLogger('security')

class SecurityAuditMiddleware(MiddlewareMixin):
    """
    Middleware to log security-sensitive events.
    """
    def process_request(self, request):
        pass

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = get_client_ip(request)
    logger.info(f"SUCCESSFUL_LOGIN: User '{user.username}' logged in from IP {ip}")

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    ip = get_client_ip(request)
    username = credentials.get('username', 'unknown')
    logger.warning(f"FAILED_LOGIN: Attempt for user '{username}' from IP {ip}")

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        ip = get_client_ip(request)
        logger.info(f"SUCCESSFUL_LOGOUT: User '{user.username}' logged out from IP {ip}")

@receiver(m2m_changed, sender=User.user_permissions.through)
@receiver(m2m_changed, sender=User.groups.through)
def log_user_privilege_change(sender, instance, action, pk_set, **kwargs):
    """
    Logs changes to user permissions or groups.
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        user = instance
        logger.info(f"PRIVILEGE_CHANGE: Permissions or groups modified for user '{user.username}'. Action: {action}, Change count: {len(pk_set) if pk_set else 'all'}")
