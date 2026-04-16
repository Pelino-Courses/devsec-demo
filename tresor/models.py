import os
import uuid

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

AVATAR_MAX_BYTES = 2 * 1024 * 1024
DOCUMENT_MAX_BYTES = 5 * 1024 * 1024


def avatar_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return os.path.join('avatars', uuid.uuid4().hex + ext)


def document_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return os.path.join('documents', uuid.uuid4().hex + ext)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    avatar = models.FileField(upload_to=avatar_upload_path, blank=True)

    def __str__(self):
        return f"{self.user.username} profile"


class Document(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to=document_upload_path)
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.owner.username} — {self.original_name}"


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
