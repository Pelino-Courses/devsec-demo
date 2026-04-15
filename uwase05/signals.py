from django.contrib.auth.models import Group, User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile
from .authorization import STUDENT_GROUP


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        student_group, _ = Group.objects.get_or_create(name=STUDENT_GROUP)
        instance.groups.add(student_group)
