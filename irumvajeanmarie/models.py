from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    ROLE_STUDENT = 'student'
    ROLE_INSTRUCTOR = 'instructor'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Student'),
        (ROLE_INSTRUCTOR, 'Instructor'),
        (ROLE_ADMIN, 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, default='')
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_STUDENT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def is_instructor(self):
        return self.role == self.ROLE_INSTRUCTOR

    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    def is_student(self):
        return self.role == self.ROLE_STUDENT


class LoginAttempt(models.Model):
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    was_successful = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} - {'Success' if self.was_successful else 'Failure'} at {self.timestamp}"


class AccountLockout(models.Model):
    username = models.CharField(max_length=150, unique=True)
    locked_until = models.DateTimeField()

    def __str__(self):
        return f"{self.username} locked until {self.locked_until}"