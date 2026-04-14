from django.test import TestCase
from django.contrib.auth.models import User, Group, Permission
from django.urls import reverse
from django.core import mail
from .models import Profile

class AuthenticationTests(TestCase):
    
    def setUp(self):
        """Set up test data"""
        self.test_user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
    
    def test_user_registration_success(self):
        """Test successful user registration with email"""
        response = self.client.post(reverse('Munyabugingo:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'complexpass123!',
            'password2': 'complexpass123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser', email='new@example.com').exists())

    def test_profile_update_success(self):
        """Test successful profile update"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('Munyabugingo:profile'), {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com'
        })
        self.test_user.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.test_user.first_name, 'Updated')
        self.assertEqual(self.test_user.email, 'updated@example.com')

    def test_password_change_success(self):
        """Test successful password change"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('Munyabugingo:password_change'), {
            'old_password': 'testpass123',
            'new_password1': 'NewPass123!',
            'new_password2': 'NewPass123!',
        })
        self.assertEqual(response.status_code, 302)
        # Verify can login with new password
        self.assertTrue(self.client.login(username='testuser', password='NewPass123!'))
    
    def test_user_registration_password_mismatch(self):
        """Test registration with mismatched passwords"""
        response = self.client.post(reverse('Munyabugingo:register'), {
            'username': 'newuser',
            'password1': 'password123',
            'password2': 'different123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())
    
    def test_login_success(self):
        """Test successful login"""
        response = self.client.post(reverse('Munyabugingo:login'), {
            'username': 'testuser',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)
    
    def test_protected_dashboard_requires_login(self):
        """Test that dashboard requires authentication"""
        response = self.client.get(reverse('Munyabugingo:dashboard'))
        self.assertEqual(response.status_code, 302)
    
    def test_authenticated_user_can_access_dashboard(self):
        """Test authenticated user can access dashboard"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('Munyabugingo:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WELCOME')
        self.assertContains(response, 'testuser')

    def test_standard_user_cannot_access_admin_dashboard(self):
        """Test authenticated user without permission gets 403 on admin dashboard"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('Munyabugingo:admin_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_privileged_user_can_access_admin_dashboard(self):
        """Test privileged user can access admin dashboard"""
        # Create privileged user and add permission
        privileged_user = User.objects.create_user(
            username='privuser',
            password='testpass123',
            email='priv@example.com'
        )
        permission = Permission.objects.get(codename='can_view_admin_dashboard')
        privileged_user.user_permissions.add(permission)
        
        self.client.login(username='privuser', password='testpass123')
        response = self.client.get(reverse('Munyabugingo:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Management')

    def test_user_can_view_own_profile_detail(self):
        """Test user can successfully view their own profile detail page"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('Munyabugingo:profile_detail', kwargs={'pk': self.test_user.profile.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')

    def test_user_cannot_view_other_profile_detail_idor(self):
        """Test user cannot view another user's profile detail (IDOR Prevention)"""
        # Create another user
        other_user = User.objects.create_user(username='other', password='pass')
        
        self.client.login(username='testuser', password='testpass123')
        # Attempt to access other_user's profile
        response = self.client.get(reverse('Munyabugingo:profile_detail', kwargs={'pk': other_user.profile.pk}))
        # Should be forbidden
        self.assertEqual(response.status_code, 403)

    def test_admin_can_view_any_profile_detail(self):
        """Test privileged user can view any profile detail page"""
        # Create privileged user
        privileged_user = User.objects.create_user(username='admin_user', password='pass')
        perm = Permission.objects.get(codename='can_view_admin_dashboard')
        privileged_user.user_permissions.add(perm)
        
        # Create a victim user
        victim = User.objects.create_user(username='victim', password='pass')
        
        self.client.login(username='admin_user', password='pass')
        response = self.client.get(reverse('Munyabugingo:profile_detail', kwargs={'pk': victim.profile.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'victim')

    def test_password_reset_request_sends_email(self):
        """Test that a password reset request actually sends an email"""
        response = self.client.post(reverse('Munyabugingo:password_reset'), {
            'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 302)
        # Check that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)
        # Verify recipient
        self.assertEqual(mail.outbox[0].to, ['test@example.com'])
        self.assertIn('password reset', mail.outbox[0].body)

    def test_password_reset_enumeration_protection(self):
        """Test that resetting a non-existent email still redirects to success page (Enumeration Protection)"""
        response = self.client.post(reverse('Munyabugingo:password_reset'), {
            'email': 'nonexistent@example.com'
        })
        # Should redirect to the "done" page using idiomatic Django check
        self.assertRedirects(response, reverse('Munyabugingo:password_reset_done'))
        # No email should be sent for non-existent users
        self.assertEqual(len(mail.outbox), 0)
