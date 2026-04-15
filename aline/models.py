from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):
    """
    Extended user profile model to store additional student information.
    
    This model extends Django's built-in User model with application-specific
    fields for student management while maintaining security best practices.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    student_id = models.CharField(
        max_length=20,
        unique=True,
        help_text=_('Unique student identifier')
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text=_("Student's date of birth")
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Contact phone number')
    )
    bio = models.TextField(
        blank=True,
        max_length=500,
        help_text=_('Brief biography or about section')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('user profile')
        verbose_name_plural = _('user profiles')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.student_id})"
