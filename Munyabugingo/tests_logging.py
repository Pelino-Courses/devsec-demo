import logging
from django.test import TestCase, override_settings
from django.contrib.auth.models import User, Group
from django.urls import reverse
from io import StringIO

class AuditLoggingTests(TestCase):
    """Verify that security-relevant events generate proper audit logs"""

    def setUp(self):
        # Clear existing logs if any
        self.user = User.objects.create_user(username='audituser', password='password123')
        self.login_url = reverse('Munyabugingo:login')
        self.logout_url = reverse('Munyabugingo:logout')
        self.register_url = reverse('Munyabugingo:register')
        
        # Use a string buffer to capture logs for inspection
        self.log_output = StringIO()
        self.handler = logging.StreamHandler(self.log_output)
        self.logger = logging.getLogger('Munyabugingo.audit')
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def test_login_success_logs_event(self):
        """Successful login should generate an AUDIT log"""
        self.client.post(self.login_url, {'username': 'audituser', 'password': 'password123'})
        log_contents = self.log_output.getvalue()
        self.assertIn('[LOGIN_SUCCESS]', log_contents)
        self.assertIn('user=audituser', log_contents)

    def test_login_failure_logs_event(self):
        """Failed login should generate an AUDIT log with IP"""
        self.client.post(self.login_url, {'username': 'audituser', 'password': 'wrongpassword'})
        log_contents = self.log_output.getvalue()
        self.assertIn('[LOGIN_FAILURE]', log_contents)
        self.assertIn('user=ANONYMOUS', log_contents)
        self.assertIn('status=FAILURE', log_contents)

    def test_logout_logs_event(self):
        """User logout should generate an AUDIT log"""
        self.client.login(username='audituser', password='password123')
        self.client.post(self.logout_url)
        log_contents = self.log_output.getvalue()
        self.assertIn('[LOGOUT]', log_contents)
        self.assertIn('user=audituser', log_contents)

    def test_registration_logs_event(self):
        """New user registration should generate an AUDIT log"""
        self.client.post(self.register_url, {
            'username': 'newaudituser',
            'email': 'audit@test.com',
            'password1': 'NewPass123!',
            'password2': 'NewPass123!'
        })
        log_contents = self.log_output.getvalue()
        self.assertIn('[USER_REGISTRATION]', log_contents)
        self.assertIn('user=newaudituser', log_contents)

    def test_privilege_change_logs_event(self):
        """Adding a user to a group should generate a PRIVILEGE_UPGRADE log"""
        group, _ = Group.objects.get_or_create(name='Privileged Users')
        self.user.groups.add(group)
        log_contents = self.log_output.getvalue()
        self.assertIn('[PRIVILEGE_UPGRADE]', log_contents)
        self.assertIn('user=audituser', log_contents)
        self.assertIn('Privileged Users', log_contents)

    def test_no_password_logging(self):
        """Ensure that raw passwords never appear in logs even in metadata"""
        # Attempt login with a very unique password to search for it
        secret_password = "SUPER_SECRET_UNLOGGED_PASS_999"
        self.client.post(self.login_url, {'username': 'audituser', 'password': secret_password})
        log_contents = self.log_output.getvalue()
        self.assertNotIn(secret_password, log_contents, "Sensitive password data found in audit logs!")
