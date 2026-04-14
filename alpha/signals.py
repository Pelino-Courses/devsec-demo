import logging
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save, m2m_changed
from django.contrib.auth.models import User
from django.dispatch import receiver

# Initialize our specific audit logger defined mathematically inside settings.py
audit_logger = logging.getLogger('security.audit')

def get_client_ip(request):
    """Safely extracts IP traversing proxied domains"""
    if not request:
        return 'unknown'
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR', 'unknown')
    return ip

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = get_client_ip(request)
    audit_logger.info(f"AUDIT_EVENT: [LOGIN_SUCCESS] User '{user.username}' successfully authenticated from IP {ip}.")

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    ip = get_client_ip(request)
    username = user.username if user else 'Anonymous'
    audit_logger.info(f"AUDIT_EVENT: [LOGOUT] User '{username}' ended their session from IP {ip}.")

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    ip = get_client_ip(request)
    # Be exquisitely careful to NEVER log raw password properties from `credentials`!
    username = credentials.get('username', 'unknown')
    audit_logger.warning(f"AUDIT_EVENT: [LOGIN_FAILED] Invalid authentication attempt for username '{username}' from IP {ip}.")

@receiver(post_save, sender=User)
def log_password_change(sender, instance, created, update_fields, **kwargs):
    # Only log on explicit password modifications or creations mappings
    if not created and update_fields and 'password' in update_fields:
        audit_logger.info(f"AUDIT_EVENT: [PASSWORD_CHANGED] Password hash rotated for User '{instance.username}'.")

@receiver(m2m_changed, sender=User.groups.through)
def log_user_groups_changed(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        audit_logger.info(f"AUDIT_EVENT: [PRIVILEGE_CHANGE] Group boundaries modified '{action}' resolving onto User '{instance.username}'.")

@receiver(m2m_changed, sender=User.user_permissions.through)
def log_user_permissions_changed(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        audit_logger.info(f"AUDIT_EVENT: [PRIVILEGE_CHANGE] Abstract permissions assigned/removed '{action}' natively mapping onto User '{instance.username}'.")
