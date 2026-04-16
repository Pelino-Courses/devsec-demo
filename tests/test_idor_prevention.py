"""
Tests for IDOR (Insecure Direct Object Reference) prevention in user profile and account management views.

This test suite verifies that:
1. Users cannot view other users' profiles
2. Users cannot modify other users' profiles
3. Admins cannot change their own role
4. Proper 403 Forbidden responses are returned for unauthorized access
5. Privileged users can access restricted data
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from justin.models import Profile, Role


class IDORProfileAccessTestCase(TestCase):
    """Test IDOR prevention for user profile access."""
    
    def setUp(self):
        """Set up test users with different roles."""
        self.client = Client()
        
        # Create standard user
        self.standard_user = User.objects.create_user(
            username='student1',
            email='student1@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=self.standard_user, role=Role.USER)
        
        # Create another standard user
        self.other_student = User.objects.create_user(
            username='student2',
            email='student2@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=self.other_student, role=Role.USER)
        
        # Create privileged user (instructor)
        self.instructor = User.objects.create_user(
            username='instructor1',
            email='instructor@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=self.instructor, role=Role.INSTRUCTOR)
        
        # Create admin user
        self.admin = User.objects.create_user(
            username='admin1',
            email='admin@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=self.admin, role=Role.ADMIN)
    
    def test_user_cannot_view_other_user_profile(self):
        """Standard user should not be able to view another user's profile."""
        self.client.login(username='student1', password='testpass123')
        
        # Try to view another user's profile
        url = reverse('view_user_profile', args=[self.other_student.id])
        response = self.client.get(url)
        
        # Should get 403 Forbidden
        self.assertEqual(response.status_code, 403)
        self.assertIn('permission', response.content.decode().lower())
    
    def test_user_can_view_own_profile(self):
        """User should be able to view their own profile."""
        self.client.login(username='student1', password='testpass123')
        
        # View own profile
        url = reverse('view_user_profile', args=[self.standard_user.id])
        response = self.client.get(url)
        
        # Should succeed
        self.assertEqual(response.status_code, 200)
    
    def test_privileged_user_can_view_any_profile(self):
        """Privileged users (instructors, staff, admins) should view any profile."""
        self.client.login(username='instructor1', password='testpass123')
        
        # Instructor should be able to view student's profile
        url = reverse('view_user_profile', args=[self.standard_user.id])
        response = self.client.get(url)
        
        # Should succeed
        self.assertEqual(response.status_code, 200)
    
    def test_unauthenticated_cannot_view_profile(self):
        """Unauthenticated users should not access profile views."""
        url = reverse('view_user_profile', args=[self.standard_user.id])
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_view_nonexistent_profile_returns_404(self):
        """Accessing a non-existent profile should return 404."""
        self.client.login(username='student1', password='testpass123')
        
        url = reverse('view_user_profile', args=[9999])
        response = self.client.get(url)
        
        # Should return 404
        self.assertEqual(response.status_code, 404)


class IDORProfileUpdateTestCase(TestCase):
    """Test IDOR prevention for profile updates."""
    
    def setUp(self):
        """Set up test users."""
        self.client = Client()
        
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=self.user1, role=Role.USER)
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=self.user2, role=Role.USER)
    
    def test_user_can_update_own_profile(self):
        """User should be able to update their own profile."""
        self.client.login(username='user1', password='testpass123')
        
        url = reverse('update_profile')
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'image_url': 'https://example.com/pic.jpg',
            'bio': 'Test bio'
        }
        response = self.client.post(url, data)
        
        # Should redirect to profile after successful update
        self.assertEqual(response.status_code, 302)
        self.assertIn('profile', response.url)
        
        # Verify the update was saved
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.first_name, 'John')
        self.assertEqual(self.user1.email, 'john@example.com')
    
    def test_profile_update_requires_authentication(self):
        """Profile update should require authentication."""
        url = reverse('update_profile')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


class IDORRoleChangeTestCase(TestCase):
    """Test IDOR prevention for role changes."""
    
    def setUp(self):
        """Set up test users with different roles."""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=self.user, role=Role.USER)
        
        self.other_user = User.objects.create_user(
            username='other_student',
            email='other@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=self.other_user, role=Role.USER)
        
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=self.admin, role=Role.ADMIN)
    
    def test_non_admin_cannot_change_roles(self):
        """Non-admin users should not be able to change roles."""
        self.client.login(username='student', password='testpass123')
        
        url = reverse('change_user_role', args=[self.other_user.id])
        response = self.client.get(url)
        
        # Should get 403 Forbidden
        self.assertEqual(response.status_code, 403)
    
    def test_admin_cannot_change_own_role(self):
        """Admin should not be able to change their own role (IDOR prevention)."""
        self.client.login(username='admin', password='testpass123')
        
        url = reverse('change_user_role', args=[self.admin.id])
        data = {'role': 'user'}
        response = self.client.post(url, data)
        
        # Should get 302 redirect with warning message
        self.assertEqual(response.status_code, 302)
        
        # Verify role was NOT changed
        self.admin.profile.refresh_from_db()
        self.assertEqual(self.admin.profile.role, Role.ADMIN)
    
    def test_admin_can_change_other_user_role(self):
        """Admin should be able to change other users' roles."""
        self.client.login(username='admin', password='testpass123')
        
        url = reverse('change_user_role', args=[self.user.id])
        data = {'role': 'instructor'}
        response = self.client.post(url, data)
        
        # Should redirect successfully
        self.assertEqual(response.status_code, 302)
        
        # Verify role was changed
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.role, Role.INSTRUCTOR)
    
    def test_change_role_nonexistent_user(self):
        """Attempting to change role of non-existent user should handle gracefully."""
        self.client.login(username='admin', password='testpass123')
        
        url = reverse('change_user_role', args=[9999])
        response = self.client.get(url)
        
        # Should redirect with error message
        self.assertEqual(response.status_code, 302)
    
    def test_invalid_role_change_rejected(self):
        """Attempting to set invalid role should be rejected."""
        self.client.login(username='admin', password='testpass123')
        
        url = reverse('change_user_role', args=[self.user.id])
        data = {'role': 'invalid_role_xyz'}
        response = self.client.post(url, data)
        
        # Should handle gracefully
        self.assertEqual(response.status_code, 302)
        
        # Verify role was NOT changed
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.role, Role.USER)
    
    def test_change_user_role_requires_admin(self):
        """Role change endpoint should require admin privileges."""
        self.client.login(username='student', password='testpass123')
        
        url = reverse('change_user_role', args=[self.other_user.id])
        response = self.client.get(url)
        
        # Should get 403 Forbidden
        self.assertEqual(response.status_code, 403)


class IDORViewAllProfilesTestCase(TestCase):
    """Test IDOR prevention for viewing all profiles."""
    
    def setUp(self):
        """Set up test users."""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=self.user, role=Role.USER)
        
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=self.instructor, role=Role.INSTRUCTOR)
    
    def test_standard_user_cannot_view_all_profiles(self):
        """Standard users should not be able to view all profiles."""
        self.client.login(username='student', password='testpass123')
        
        url = reverse('all_profiles')
        response = self.client.get(url)
        
        # Should get 403 Forbidden
        self.assertEqual(response.status_code, 403)
    
    def test_privileged_user_can_view_all_profiles(self):
        """Privileged users should be able to view all profiles."""
        self.client.login(username='instructor', password='testpass123')
        
        url = reverse('all_profiles')
        response = self.client.get(url)
        
        # Should succeed
        self.assertEqual(response.status_code, 200)
    
    def test_unauthenticated_cannot_view_all_profiles(self):
        """Unauthenticated users should not access view all profiles."""
        url = reverse('all_profiles')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


class IDORAdminDashboardTestCase(TestCase):
    """Test IDOR prevention for admin dashboard."""
    
    def setUp(self):
        """Set up test users."""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=self.user, role=Role.USER)
        
        self.privileged_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=self.privileged_user, role=Role.STAFF)
    
    def test_standard_user_cannot_access_admin_dashboard(self):
        """Standard users should not access admin dashboard."""
        self.client.login(username='student', password='testpass123')
        
        url = reverse('admin_dashboard')
        response = self.client.get(url)
        
        # Should get 403 Forbidden
        self.assertEqual(response.status_code, 403)
    
    def test_privileged_user_can_access_admin_dashboard(self):
        """Privileged users should access admin dashboard."""
        self.client.login(username='staff', password='testpass123')
        
        url = reverse('admin_dashboard')
        response = self.client.get(url)
        
        # Should succeed
        self.assertEqual(response.status_code, 200)


class IDORUserManagementTestCase(TestCase):
    """Test IDOR prevention for user management."""
    
    def setUp(self):
        """Set up test users."""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=self.user, role=Role.USER)
        
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        Profile.objects.create(user=self.admin, role=Role.ADMIN)
    
    def test_non_admin_cannot_access_user_management(self):
        """Non-admin users should not access user management."""
        self.client.login(username='student', password='testpass123')
        
        url = reverse('user_management')
        response = self.client.get(url)
        
        # Should get 403 Forbidden
        self.assertEqual(response.status_code, 403)
    
    def test_admin_can_access_user_management(self):
        """Admin users should access user management."""
        self.client.login(username='admin', password='testpass123')
        
        url = reverse('user_management')
        response = self.client.get(url)
        
        # Should succeed
        self.assertEqual(response.status_code, 200)
