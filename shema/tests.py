from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')

        self.home_url = reverse('home')
        self.username = 'testuser'
        self.password = 'TestPass123!'
        self.user = User.objects.create_user(username=self.username, password=self.password)

    def test_home_page_status_code(self):
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shema/home.html')

    def test_registration_flow(self):
        response = self.client.post(self.register_url, {
            'username': 'newuser',
            'password': 'NewPass123!',
            'password_confirm': 'NewPass123!'
        })
        # UserCreationForm usually needs password1 and password2
        # Let's check the actual field names in UserCreationForm
        # By default they are username, password1, password2
        response = self.client.post(self.register_url, {
            'username': 'newuser2',
            'password1': 'NewPass123!',
            'password2': 'NewPass123!'
        })
        self.assertEqual(response.status_code, 302) # Redirect to home
        self.assertTrue(User.objects.filter(username='newuser2').exists())

    def test_login_flow(self):
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password
        })
        self.assertEqual(response.status_code, 302) # Redirect to home
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_logout_flow(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_profile_protected_access(self):
        # Access profile without login
        profile_url = reverse('profile', kwargs={'username': self.username})
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

        # Access profile with login
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shema/profile.html')

    def test_idor_prevention_on_profile_view(self):
        # Create a second user
        user2_username = 'hacker_user'
        User.objects.create_user(username=user2_username, password='TestPass123!')
        
        # Log in as testuser
        self.client.login(username=self.username, password=self.password)
        
        # Action: Attempt to access hacker_user's profile
        hacker_profile_url = reverse('profile', kwargs={'username': user2_username})
        response = self.client.get(hacker_profile_url)
        
        # Assert IDOR prevention gracefully returns 404
        self.assertEqual(response.status_code, 404)

    def test_idor_prevention_on_profile_update(self):
        # Create a second user
        target_user = User.objects.create_user(username='target_user', password='TestPass123!')
        target_user.profile.bio = "Original Bio"
        target_user.profile.save()
        
        # Log in as testuser (the attacker)
        self.client.login(username=self.username, password=self.password)
        
        # Action: Attempt to modify target_user's bio via POST to their update URL
        update_url = reverse('update_profile', kwargs={'username': 'target_user'})
        response = self.client.post(update_url, {'bio': 'Hacked Bio'})
        
        # Assert: Access is denied
        self.assertEqual(response.status_code, 404)
        
        # Assert: Data was NOT changed
        target_user.refresh_from_db()
        self.assertEqual(target_user.profile.bio, "Original Bio")

    def test_instructor_dashboard_anonymous_access(self):
        # Anonymous users should be redirected to login
        url = reverse('instructor_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_instructor_dashboard_standard_user_access(self):
        # Normal authenticated user should get 403 Forbidden
        self.client.login(username=self.username, password=self.password)
        url = reverse('instructor_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_instructor_dashboard_privileged_user_access(self):
        # Create a privileged user and grant permission
        privileged_user = User.objects.create_user(username='instructor1', password='TestPass123!')
        from django.contrib.auth.models import Permission
        perm = Permission.objects.get(codename='view_instructor_dashboard')
        privileged_user.user_permissions.add(perm)
        
        self.client.login(username='instructor1', password='TestPass123!')
        url = reverse('instructor_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shema/instructor_dashboard.html')
