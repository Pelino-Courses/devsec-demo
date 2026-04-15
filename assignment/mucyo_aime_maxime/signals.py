import logging
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models.signals import post_save, m2m_changed

security_logger = logging.getLogger('security_audit')

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get('username', 'unknown')
    ip = request.META.get('REMOTE_ADDR')
    security_logger.warning(f"AUTH_SIGNAL_LOGIN_FAILED: Attempt for account '{username}' from IP {ip}")

@receiver(post_save, sender=User)
def log_user_privilege_change(sender, instance, created, **kwargs):
    if not created:
        # Check if staff or superuser status changed
        # Note: This is a simplified check for demo purposes
        security_logger.info(f"USER_PRIVILEGE_CHANGE: User '{instance.username}' (ID: {instance.id}) profile/status updated.")

@receiver(m2m_changed, sender=User.groups.through)
def log_group_change(sender, instance, action, pk_set, **kwargs):
    if action in ["post_add", "post_remove"]:
        security_logger.info(f"USER_GROUP_CHANGE: User '{instance.username}' (ID: {instance.id}) groups modified. Action: {action}, Groups: {pk_set}")
