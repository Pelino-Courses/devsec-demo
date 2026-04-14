from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} profile"


class LoginAttempt(models.Model):
    username = models.CharField(max_length=150, unique=True)
    attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_attempt = models.DateTimeField(auto_now=True)

    def is_locked(self):
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

    def record_failure(self):
        if self.locked_until and timezone.now() >= self.locked_until:
            self.attempts = 0
            self.locked_until = None
        self.attempts += 1
        if self.attempts >= MAX_ATTEMPTS:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=LOCKOUT_MINUTES)
        self.save()

    def record_success(self):
        self.attempts = 0
        self.locked_until = None
        self.save()

    def __str__(self):
        return f"{self.username} ({self.attempts} attempts)"
