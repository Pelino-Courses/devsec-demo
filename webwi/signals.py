from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from . import audit
from .models import Profile


User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(m2m_changed, sender=User.user_permissions.through)
def log_user_permission_change(sender, instance, action, pk_set, **kwargs):
    """Audit-log individual permission grants and revocations on a user account."""
    if action not in ('post_add', 'post_remove') or not pk_set:
        return
    for perm_id in pk_set:
        try:
            perm = Permission.objects.select_related('content_type').get(pk=perm_id)
            codename = f"{perm.content_type.app_label}.{perm.codename}"
        except Permission.DoesNotExist:
            codename = f'permission_id={perm_id}'
        if action == 'post_add':
            audit.log_permission_granted(instance.username, codename)
        else:
            audit.log_permission_revoked(instance.username, codename)
