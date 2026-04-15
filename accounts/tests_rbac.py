from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import UserProfile


class RoleBasedAccessControlTests(TestCase):
    def setUp(self):
        """Set up test users with different roles."""
        self.client = Client()
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.admin_profile = UserProfile.objects.create(
            user=self.admin_user,
            role='admin'
        )
        
        # Create editor user
        self.editor_user = User.objects.create_user(
            username='editor',
            email='editor@test.com',
            password='testpass123'
        )
        self.editor_profile = UserProfile.objects.create(
            user=self.editor_user,
            role='editor'
        )
        
        # Create viewer user
        self.viewer_user = User.objects.create_user(
            username='viewer',
            email='viewer@test.com',
            password='testpass123'
        )
        self.viewer_profile = UserProfile.objects.create(
            user=self.viewer_user,
            role='viewer'
        )
    
    def test_anonymous_cannot_access_admin_dashboard(self):
        """Anonymous users should be redirected from admin dashboard."""
        response = self.client.get('/accounts/admin/dashboard/')
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertIn('/accounts/login', response.url)
    
    def test_viewer_cannot_access_admin_dashboard(self):
        """Viewer users should not access admin dashboard."""
        self.client.login(username='viewer', password='testpass123')
        response = self.client.get('/accounts/admin/dashboard/')
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_admin_can_access_admin_dashboard(self):
        """Admin users should access admin dashboard."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get('/accounts/admin/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')
    
    def test_viewer_cannot_access_editor_panel(self):
        """Viewer users should not access editor panel."""
        self.client.login(username='viewer', password='testpass123')
        response = self.client.get('/accounts/editor/panel/')
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_editor_can_access_editor_panel(self):
        """Editor users should access editor panel."""
        self.client.login(username='editor', password='testpass123')
        response = self.client.get('/accounts/editor/panel/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editor Panel')
    
    def test_admin_can_access_editor_panel(self):
        """Admin users should also access editor panel."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get('/accounts/editor/panel/')
        self.assertEqual(response.status_code, 200)
    
    def test_authenticated_user_can_access_profile(self):
        """Any authenticated user should access their profile."""
        self.client.login(username='viewer', password='testpass123')
        response = self.client.get('/accounts/profile/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'viewer')
    
    def test_anonymous_cannot_access_profile(self):
        """Anonymous users should be redirected from profile."""
        response = self.client.get('/accounts/profile/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_admin_dashboard_shows_all_users(self):
        """Admin dashboard should show all users and their roles."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get('/accounts/admin/dashboard/')
        self.assertContains(response, 'admin')
        self.assertContains(response, 'editor')
        self.assertContains(response, 'viewer')
    
    def test_role_separation_admin_vs_viewer(self):
        """Verify strict separation between admin and viewer access."""
        # Viewer tries admin dashboard
        self.client.login(username='viewer', password='testpass123')
        response = self.client.get('/accounts/admin/dashboard/')
        self.assertNotEqual(response.status_code, 200)
        self.client.logout()
        
        # Admin accesses admin dashboard
        self.client.login(username='admin', password='testpass123')
        response = self.client.get('/accounts/admin/dashboard/')
        self.assertEqual(response.status_code, 200)
