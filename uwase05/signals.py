import logging

from django.contrib.auth.models import Group, User
from django.contrib.auth.signals import (
    user_logged_in,
    user_login_failed,
    user_logged_out,
)
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from .models import Profile
from .authorization import STUDENT_GROUP

logger = logging.getLogger('uwase05.audit')


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        student_group, _ = Group.objects.get_or_create(name=STUDENT_GROUP)
        instance.groups.add(student_group)


@receiver(user_logged_in)
def log_user_logged_in(sender, request, user, **kwargs):
    logger.info(
        'auth event=login_success username=%s ip=%s',
        user.username,
        request.META.get('REMOTE_ADDR', 'unknown'),
    )


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get('username') or credentials.get('email') or 'unknown'
    logger.info(
        'auth event=login_failed username=%s ip=%s',
        username,
        request.META.get('REMOTE_ADDR', 'unknown') if request is not None else 'unknown',
    )


@receiver(user_logged_out)
def log_user_logged_out(sender, request, user, **kwargs):
    logger.info(
        'auth event=logout username=%s ip=%s',
        user.username if user is not None else 'anonymous',
        request.META.get('REMOTE_ADDR', 'unknown') if request is not None else 'unknown',
    )


@receiver(m2m_changed, sender=User.groups.through)
def log_group_membership_change(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in ('post_add', 'post_remove') or not pk_set:
        return

    group_names = list(model.objects.filter(pk__in=pk_set).values_list('name', flat=True))
    event = 'group_added' if action == 'post_add' else 'group_removed'
    logger.info(
        'auth event=%s username=%s groups=%s',
        event,
        instance.username,
        ','.join(group_names),
    )
