import logging

from django.db.models.signals import post_save, m2m_changed
from django.contrib.auth.models import User, Group
from django.dispatch import receiver
from .models import Profile

audit_log = logging.getLogger('tresor.audit')


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()


@receiver(m2m_changed, sender=User.groups.through)
def log_role_change(sender, instance, action, pk_set, **kwargs):
    if action not in ('post_add', 'post_remove'):
        return
    verb = 'added' if action == 'post_add' else 'removed'
    for group_pk in (pk_set or set()):
        try:
            group_name = Group.objects.get(pk=group_pk).name
        except Group.DoesNotExist:
            group_name = str(group_pk)
        audit_log.info('event=auth.role_change user=%s group=%s action=%s', instance.username, group_name, verb)
