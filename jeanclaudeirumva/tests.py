from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import UserProfile


class RegistrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_page_loads(self):
        response = self.client.get(reverse('jeanclaudeirumva:register'))
        self.assertEqual(response.status_code, 200)

    def test_register_valid_user(self):
        response = self.client.post(reverse('jeanclaudeirumva:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertRedirects(response, reverse('jeanclaudeirumva:dashboard'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_creates_profile(self):
        self.client.post(reverse('jeanclaudeirumva:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        user = User.objects.get(username='newuser')
        self.assertTrue(UserProfile.objects.filter(user=user).exists())


class XSSTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='StrongPass123!'
        )
        self.profile = UserProfile.objects.create(user=self.user)
        self.client.login(username='testuser', password='StrongPass123!')

    def test_xss_script_tag_is_escaped(self):
        self.client.post(reverse('jeanclaudeirumva:profile'), {
            'bio': '<script>alert("XSS")</script>',
        })
        response = self.client.get(reverse('jeanclaudeirumva:profile'))
        self.assertNotContains(response, '<script>alert("XSS")</script>')
        self.assertContains(response, '&lt;script&gt;')

    def test_xss_img_tag_is_escaped(self):
        self.client.post(reverse('jeanclaudeirumva:profile'), {
            'bio': '<img src=x onerror=alert(1)>',
        })
        response = self.client.get(reverse('jeanclaudeirumva:profile'))
        self.assertNotContains(response, '<img src=x onerror=alert(1)>')

    def test_xss_javascript_url_is_escaped(self):
        self.client.post(reverse('jeanclaudeirumva:profile'), {
            'bio': '<a href="javascript:alert(1)">click</a>',
        })
        response = self.client.get(reverse('jeanclaudeirumva:profile'))
        self.assertNotContains(response, '<a href="javascript:alert(1)">')
        self.assertContains(response, '&lt;a href=&quot;javascript:alert(1)&quot;&gt;')

    def test_normal_text_renders_correctly(self):
        self.client.post(reverse('jeanclaudeirumva:profile'), {
            'bio': 'Hello I am a student at university.',
        })
        response = self.client.get(reverse('jeanclaudeirumva:profile'))
        self.assertContains(response, 'Hello I am a student at university.')

    def test_bio_saved_to_database(self):
        self.client.post(reverse('jeanclaudeirumva:profile'), {
            'bio': 'My safe bio text.',
        })
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, 'My safe bio text.')


class ProtectedPagesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='StrongPass123!'
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('jeanclaudeirumva:dashboard'))
        self.assertRedirects(response, '/auth/login/?next=/auth/dashboard/')

    def test_profile_requires_login(self):
        response = self.client.get(reverse('jeanclaudeirumva:profile'))
        self.assertRedirects(response, '/auth/login/?next=/auth/profile/')

    def test_dashboard_accessible_when_logged_in(self):
        self.client.login(username='testuser', password='StrongPass123!')
        response = self.client.get(reverse('jeanclaudeirumva:dashboard'))
        self.assertEqual(response.status_code, 200)


class LogoutTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='StrongPass123!'
        )
        self.client.login(username='testuser', password='StrongPass123!')

    def test_logout_requires_post(self):
        response = self.client.get(reverse('jeanclaudeirumva:logout'))
        self.assertEqual(response.status_code, 200)

    def test_logout_success(self):
        response = self.client.post(reverse('jeanclaudeirumva:logout'))
        self.assertRedirects(response, reverse('jeanclaudeirumva:login'))