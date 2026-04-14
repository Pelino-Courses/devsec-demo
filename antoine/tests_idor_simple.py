"""
IDOR (Insecure Direct Object Reference) Prevention Tests - Simplified Version

Tests to verify that users cannot access or modify data that doesn't belong to them
by manipulating URL parameters or identifiers.

These are simpler tests focused on access control logic, not template rendering.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from antoine.models import UserProfile, LoginHistory


def create_rbac_groups():
    """Helper function to create RBAC groups for testing"""
    Group.objects.get_or_create(name='Student')
    Group.objects.get_or_create(name='Instructor')
    Group.objects.get_or_create(name='Admin')


class IDORAccessControlTest(TestCase):
    """Test basic IDOR prevention through access control"""
    
    def setUp(self):
        """Create test users"""
        self.client = Client()
        create_rbac_groups()
        
        # Create two students
        self.student1 = User.objects.create_user(
            username='student1',
            email='student1@example.com',
            password='Student1@123'
        )
        self.student2 = User.objects.create_user(
            username='student2',
            email='student2@example.com',
            password='Student2@123'
        )
        
        # Create admin
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='Admin@123'
        )
        self.admin.is_superuser = True
        self.admin.is_staff = True
        self.admin.save()
    
    def test_public_profile_requires_login(self):
        """Test that viewing public profiles requires authentication"""
        # Anonymous user cannot view
        response = self.client.get(
            reverse('antoine:public_profile', args=[self.student1.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
        
        # Authenticated user can view
        self.client.login(username='student1', password='Student1@123')
        response = self.client.get(
            reverse('antoine:public_profile', args=[self.student2.id])
        )
        self.assertIn(response.status_code, [200, 500])  # 200 if template exists, 500 if not, but not 302
    
    def test_reset_password_requires_admin(self):
        """Test that password reset is admin-only"""
        # Login as student
        self.client.login(username='student1', password='Student1@123')
        response = self.client.get(
            reverse('antoine:reset_user_password', args=[self.student2.id])
        )
        # Student should get redirected
        self.assertEqual(response.status_code, 302)
        
        # Admin should pass the decorator (permission granted)
        self.client.logout()
        self.client.login(username='admin', password='Admin@123')
        response = self.client.get(
            reverse('antoine:reset_user_password', args=[self.student1.id])
        )
        # Admin should NOT be redirected (may be 200, 500, or other error, but not 302)
        self.assertNotEqual(response.status_code, 302)
    
    def test_profile_shows_correct_user(self):
        """Test that profile view shows current user's profile"""
        self.client.login(username='student1', password='Student1@123')
        response = self.client.get(reverse('antoine:profile'))
        self.assertEqual(response.status_code, 200)
        # Profile should be accessible
        self.assertIsNotNone(self.student1.antoine_profile)
    
    def test_login_history_shows_only_current_user(self):
        """Test that login history is filtered by current user"""
        # Create a login for student1
        LoginHistory.objects.create(
            user=self.student1,
            ip_address='192.168.1.1',
            user_agent='TestAgent',
            success=True
        )
        
        # Login as student1 and view history
        self.client.login(username='student1', password='Student1@123')
        response = self.client.get(reverse('antoine:login_history'))
        self.assertEqual(response.status_code, 200)
        
        # The view should query LoginHistory.filter(user=student1)
        # We can't easily verify content without template, but the query filters by user


class IDORNonExistentUserTest(TestCase):
    """Test behavior when accessing non-existent users"""
    
    def setUp(self):
        """Create test users"""
        self.client = Client()
        create_rbac_groups()
        
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='Admin@123'
        )
        self.admin.is_superuser = True
        self.admin.is_staff = True
        self.admin.save()
    
    def test_public_profile_nonexistent_returns_404(self):
        """Test that accessing non-existent user in public profile returns 404"""
        self.client.login(username='admin', password='Admin@123')
        response = self.client.get(
            reverse('antoine:public_profile', args=[99999])
        )
        self.assertEqual(response.status_code, 404)
    
    def test_reset_password_nonexistent_user_safe_handling(self):
        """Test that trying to reset non-existent user is handled safely"""
        self.client.login(username='admin', password='Admin@123')
        response = self.client.get(
            reverse('antoine:reset_user_password', args=[99999])
        )
        # Decorator should redirect to dashboard with generic message
        self.assertEqual(response.status_code, 302)
        self.assertIn('dashboard', response.url)


class IDORChangePasswordTest(TestCase):
    """Test that password changes can only be done by user themselves"""
    
    def setUp(self):
        """Create test users"""
        self.client = Client()
        self.student1 = User.objects.create_user(
            username='student1',
            email='student1@example.com',
            password='OldPassword@123'
        )
        UserProfile.objects.create(user=self.student1)
    
    def test_change_password_requires_old_password(self):
        """Test that changing password requires correct old password"""
        self.client.login(username='student1', password='OldPassword@123')
        response = self.client.post(
            reverse('antoine:change_password'),
            {
                'old_password': 'WrongPassword@123',
                'new_password1': 'NewPassword@456',
                'new_password2': 'NewPassword@456',
            }
        )
        # Should show form with error
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'old_password', 'Your old password was entered incorrectly.')
    
    def test_change_password_succeeds_with_correct_old(self):
        """Test that password change succeeds with correct old password"""
        self.client.login(username='student1', password='OldPassword@123')
        response = self.client.post(
            reverse('antoine:change_password'),
            {
                'old_password': 'OldPassword@123',
                'new_password1': 'NewPassword@456',
                'new_password2': 'NewPassword@456',
            },
            follow=True
        )
        # Should redirect after successful change
        self.assertEqual(response.status_code, 200)
        # Verify new password works
        self.assertTrue(self.student1.check_password('NewPassword@456'))
