from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import m2m_changed, post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .utils import log_audit_event
from .models import Profile

@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if user:
        log_audit_event('LOGOUT', user=user, request=request)

@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    log_audit_event('LOGIN_FAILURE', status='FAILURE_SIGNAL', request=request, metadata={'username': credentials.get('username')})

@receiver(m2m_changed, sender=User.groups.through)
def on_user_groups_changed(sender, instance, action, pk_set, **kwargs):
    """Log changes to user group memberships (privilege changes)"""
    if action in ["post_add", "post_remove"]:
        event_type = 'PRIVILEGE_UPGRADE' if action == "post_add" else 'PRIVILEGE_DOWNGRADE'
        from django.contrib.auth.models import Group
        groups = list(Group.objects.filter(pk__in=pk_set).values_list('name', flat=True))
        log_audit_event(event_type, user=instance, status=action.upper(), metadata={'groups': groups})

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        # Assign new users to Standard Users group by default
        from django.contrib.auth.models import Group
        standard_group, _ = Group.objects.get_or_create(name='Standard Users')
        instance.groups.add(standard_group)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
