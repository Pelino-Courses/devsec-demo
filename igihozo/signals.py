from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .authz import assign_default_role, ensure_role_groups
from .models import Profile


@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, display_name=instance.get_username())
        assign_default_role(instance)
        return

    Profile.objects.get_or_create(
        user=instance,
        defaults={"display_name": instance.get_username()},
    )


@receiver(post_migrate)
def create_role_groups(sender, **kwargs):
    if sender.name == "igihozo":
        ensure_role_groups()
