from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import AuditLog, UserProfile

class AuditLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        UserProfile.objects.get_or_create(user=self.user, role='viewer')
        self.login_url = reverse('login')
        self.register_url = reverse('register')

    def test_login_success_logs_event(self):
        """Verify that a successful login creates an AuditLog record."""
        self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'password123',
        })
        log = AuditLog.objects.filter(user=self.user, event_type='login_success').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.ip_address, '127.0.0.1')

    def test_login_failure_logs_event(self):
        """Verify that a failed login attempt is recorded."""
        self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpassword',
        })
        log = AuditLog.objects.filter(username_attempted='testuser', event_type='login_failure').first()
        self.assertIsNotNone(log)
        self.assertIn('Invalid credentials', log.details)

    def test_registration_logs_event(self):
        """Verify that user registration is logged."""
        self.client.post(self.register_url, {
            'username': 'newuser',
            'password1': 'password123!',
            'password2': 'password123!',
        })
        new_user = User.objects.get(username='newuser')
        log = AuditLog.objects.filter(user=new_user, event_type='registration').first()
        self.assertIsNotNone(log)

    def test_privilege_change_logs_event(self):
        """Verify that admin-driven role changes are audited."""
        admin_user = User.objects.create_superuser(username='admin', password='adminpassword', email='admin@test.com')
        UserProfile.objects.create(user=admin_user, role='admin')
        
        other_user = User.objects.create_user(username='other', password='password')
        UserProfile.objects.create(user=other_user, role='viewer')
        
        self.client.login(username='admin', password='adminpassword')
        
        self.client.post(reverse('update_role', args=[other_user.id]), {
            'role': 'editor'
        })
        
        log = AuditLog.objects.filter(event_type='privilege_change').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user, admin_user)
        self.assertIn('viewer -> editor', log.details)
        self.assertIn('other', log.details)
