from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Profile, Role
from django.urls import reverse


class RoleBasedAccessControlTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.standard_user = User.objects.create_user(
            username='standard',
            email='standard@test.com',
            password='testpass123'
        )
        self.standard_profile = Profile.objects.create(
            user=self.standard_user,
            role=Role.USER
        )
        
        self.privileged_user = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123'
        )
        self.privileged_profile = Profile.objects.create(
            user=self.privileged_user,
            role=Role.INSTRUCTOR
        )
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.admin_profile = Profile.objects.create(
            user=self.admin_user,
            role=Role.ADMIN
        )
    
    def test_anonymous_access_login(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
    
    def test_anonymous_access_register(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
    
    def test_anonymous_cannot_access_profile(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)
    
    def test_standard_user_can_access_profile(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
    
    def test_standard_user_cannot_access_admin_dashboard(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 403)
    
    def test_standard_user_cannot_access_user_management(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('user_management'))
        self.assertEqual(response.status_code, 403)
    
    def test_privileged_user_can_access_admin_dashboard(self):
        self.client.login(username='instructor', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_privileged_user_cannot_access_user_management(self):
        self.client.login(username='instructor', password='testpass123')
        response = self.client.get(reverse('user_management'))
        self.assertEqual(response.status_code, 403)
    
    def test_admin_user_can_access_user_management(self):
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('user_management'))
        self.assertEqual(response.status_code, 200)
    
    def test_privileged_user_can_access_all_profiles(self):
        self.client.login(username='instructor', password='testpass123')
        response = self.client.get(reverse('all_profiles'))
        self.assertEqual(response.status_code, 200)
    
    def test_standard_user_cannot_access_all_profiles(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('all_profiles'))
        self.assertEqual(response.status_code, 403)
    
    def test_standard_user_can_change_password(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('password_change'))
        self.assertEqual(response.status_code, 200)
    
    def test_standard_user_can_update_profile(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('update_profile'))
        self.assertEqual(response.status_code, 200)
    
    def test_403_template_rendered_for_denied_access(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'justin/403.html')
    
    def test_profile_role_property(self):
        self.assertFalse(self.standard_profile.is_privileged)
        self.assertFalse(self.standard_profile.is_admin)
        
        self.assertTrue(self.privileged_profile.is_privileged)
        self.assertFalse(self.privileged_profile.is_admin)
        
        self.assertTrue(self.admin_profile.is_privileged)
        self.assertTrue(self.admin_profile.is_admin)
    
    def test_role_context_for_authenticated_user(self):
        self.client.login(username='instructor', password='testpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_privileged'])
        self.assertFalse(response.context['is_admin'])
        self.assertEqual(response.context['user_role'], 'instructor')
    
    def test_role_context_for_anonymous_user(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_privileged'])
        self.assertFalse(response.context['is_admin'])
