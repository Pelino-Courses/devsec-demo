from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} profile"

    class Meta:
        permissions = [
            ("can_view_all_profiles", "Can view all user profiles"),
            ("can_manage_users", "Can promote or demote users"),
        ]
