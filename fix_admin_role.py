#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devsec_demo.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile

# Get admin user and update role
admin_user = User.objects.get(username='admin')
profile = UserProfile.objects.get(user=admin_user)
profile.role = 'admin'
profile.save()
print(f"✓ Updated {admin_user.username} role to: {profile.role}")
