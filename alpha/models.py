from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)

    class Meta:
        permissions = [
            ("can_view_dashboard", "Can view instructor dashboard"),
        ]

    def __str__(self):
        return self.user.username
