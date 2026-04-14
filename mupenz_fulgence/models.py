from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    """
    Extends the built-in User model with additional personal information.
    Linked via OneToOneField so each User has exactly one Profile.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    bio = models.TextField(blank=True, max_length=500)
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'

    def __str__(self):
        return f'{self.user.username} — Profile'

    def get_display_name(self):
        """Return full name when available, otherwise fall back to username."""
        return self.user.get_full_name() or self.user.username
