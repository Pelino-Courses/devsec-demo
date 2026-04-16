from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType


class Role(models.TextChoices):
    USER = 'user', 'Standard User'
    INSTRUCTOR = 'instructor', 'Instructor'
    STAFF = 'staff', 'Staff'
    ADMIN = 'admin', 'Administrator'


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    image_url = models.URLField(blank=True, help_text='URL to profile picture (e.g., from gravatar)')
    bio = models.TextField(blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} Profile'

    @property
    def get_image_url(self):
        if self.image_url:
            return self.image_url
        return None

    @property
    def is_privileged(self):
        return self.role in [Role.INSTRUCTOR, Role.STAFF, Role.ADMIN]

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._update_user_permissions()

    def _update_user_permissions(self):
        privileged_group, _ = Group.objects.get_or_create(name='Privileged')
        standard_group, _ = Group.objects.get_or_create(name='Standard')

        if self.is_privileged:
            self.user.groups.add(privileged_group)
            self.user.groups.remove(standard_group)
            if not self.user.is_staff:
                self.user.is_staff = self.role == Role.ADMIN
                self.user.save(update_fields=['is_staff'])
        else:
            self.user.groups.add(standard_group)
            self.user.groups.remove(privileged_group)


def create_role_groups():
    """Initialize role groups with appropriate permissions."""
    privileged_group, created = Group.objects.get_or_create(name='Privileged')
    standard_group, created = Group.objects.get_or_create(name='Standard')

    content_type = ContentType.objects.get_for_model(Profile)

    view_privileged_permission, _ = Permission.objects.get_or_create(
        codename='view_privileged',
        name='Can view privileged content',
        content_type=content_type,
    )
    manage_users_permission, _ = Permission.objects.get_or_create(
        codename='manage_users',
        name='Can manage users',
        content_type=content_type,
    )
    view_all_profiles_permission, _ = Permission.objects.get_or_create(
        codename='view_all_profiles',
        name='Can view all profiles',
        content_type=content_type,
    )

    privileged_group.permissions.add(
        view_privileged_permission,
        manage_users_permission,
        view_all_profiles_permission,
    )

    standard_group.permissions.add(view_privileged_permission)