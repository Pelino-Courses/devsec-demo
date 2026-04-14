from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

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