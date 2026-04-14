from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.username} - Profile"


class LoginAttempt(models.Model):
    username = models.CharField(max_length=150)
    attempts = models.IntegerField(default=0)
    last_attempt = models.DateTimeField(default=timezone.now)
    locked_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.username} - {self.attempts} attempts"

    def is_locked(self):
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

    def reset(self):
        self.attempts = 0
        self.locked_until = None
        self.save()

    def increment(self):
        self.attempts += 1
        self.last_attempt = timezone.now()
        if self.attempts >= 5:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=10)
        self.save()
