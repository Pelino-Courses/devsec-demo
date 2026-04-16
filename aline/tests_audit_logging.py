"""
Tests for audit logging in the Aline UAS application.
Verifies that security-relevant events are logged properly without leaking sensitive info.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from aline.models import UserProfile

class AuditLoggingTestCase(TestCase):
    """Test cases for verifying audit logging features."""

    def setUp(self):
        self.client = Client()
        self.username = 'audit_test_user'
        self.password = 'Audit123!Secure'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email='audit@example.com'
        )
        
        self.admin_user = User.objects.create_superuser(
            username='audit_admin',
            password='AdminPassword123!',
            email='admin@example.com'
        )
        
        self.student_group, _ = Group.objects.get_or_create(name='Student')
        self.staff_group, _ = Group.objects.get_or_create(name='Staff')

    def test_login_success_logging(self):
        """Verify successful login generates an appropriate audit log."""
        login_url = reverse('aline:login')
        with self.assertLogs('aline.audit', level='INFO') as cm:
            self.client.post(login_url, {'username': self.username, 'password': self.password})
            
        self.assertTrue(any('Login - Username: audit_test_user' in output for output in cm.output))
        self.assertTrue(any('Status: Success' in output for output in cm.output))
        self.assertFalse(any(self.password in output for output in cm.output))

    def test_login_failure_logging(self):
        """Verify failed login generates a warning log without the password."""
        login_url = reverse('aline:login')
        wrong_password = 'WrongPassword!'
        with self.assertLogs('aline.audit', level='WARNING') as cm:
            self.client.post(login_url, {'username': self.username, 'password': wrong_password})
            
        self.assertTrue(any('Login - Username: audit_test_user' in output for output in cm.output))
        self.assertTrue(any('Status: Failure' in output for output in cm.output))
        self.assertFalse(any(wrong_password in output for output in cm.output))

    def test_logout_logging(self):
        """Verify logout generates an audit log."""
        self.client.login(username=self.username, password=self.password)
        logout_url = reverse('aline:logout')
        
        with self.assertLogs('aline.audit', level='INFO') as cm:
            self.client.post(logout_url)
            
        self.assertTrue(any('Logout - Username: audit_test_user' in output for output in cm.output))

    def test_privilege_change_logging(self):
        """Verify assigning new groups to a user generates an audit log."""
        self.client.login(username='audit_admin', password='AdminPassword123!')
        detail_url = reverse('aline:user_detail', args=[self.user.id])
        
        with self.assertLogs('aline.audit', level='INFO') as cm:
            self.client.post(detail_url, {
                'groups': [self.staff_group.id],
                'is_staff': 'on'
            })
            
        log_output = "\n".join(cm.output)
        self.assertIn('Privilege Change - Target: audit_test_user', log_output)
        self.assertIn('Actor: audit_admin', log_output)
        self.assertIn('Staff: True', log_output)
