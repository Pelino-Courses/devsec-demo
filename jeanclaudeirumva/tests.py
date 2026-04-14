import io
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from .models import UserProfile


def create_test_image(name='test.jpg', format='JPEG'):
    """Create a valid test image in memory."""
    img = Image.new('RGB', (100, 100), color='red')
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type='image/jpeg')


def create_test_file(name='test.txt', content=b'Hello World', content_type='text/plain'):
    """Create a simple test file."""
    return SimpleUploadedFile(name, content, content_type=content_type)


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


class AvatarUploadTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='StrongPass123!'
        )
        self.profile = UserProfile.objects.create(user=self.user)
        self.client.login(username='testuser', password='StrongPass123!')

    def test_avatar_upload_page_loads(self):
        response = self.client.get(reverse('jeanclaudeirumva:upload_avatar'))
        self.assertEqual(response.status_code, 200)

    def test_valid_avatar_upload(self):
        image = create_test_image()
        response = self.client.post(
            reverse('jeanclaudeirumva:upload_avatar'),
            {'avatar': image},
        )
        self.assertRedirects(response, reverse('jeanclaudeirumva:profile'))

    def test_invalid_avatar_extension_rejected(self):
        bad_file = create_test_file(
            name='malicious.exe',
            content=b'MZ fake exe',
            content_type='application/octet-stream'
        )
        response = self.client.post(
            reverse('jeanclaudeirumva:upload_avatar'),
            {'avatar': bad_file},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid file')

    def test_avatar_upload_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('jeanclaudeirumva:upload_avatar'))
        self.assertEqual(response.status_code, 302)


class DocumentUploadTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='StrongPass123!'
        )
        self.profile = UserProfile.objects.create(user=self.user)
        self.client.login(username='testuser', password='StrongPass123!')

    def test_document_upload_page_loads(self):
        response = self.client.get(reverse('jeanclaudeirumva:upload_document'))
        self.assertEqual(response.status_code, 200)

    def test_valid_document_upload(self):
        doc = create_test_file(
            name='report.txt',
            content=b'This is a report.',
            content_type='text/plain'
        )
        response = self.client.post(
            reverse('jeanclaudeirumva:upload_document'),
            {'document': doc},
        )
        self.assertRedirects(response, reverse('jeanclaudeirumva:profile'))

    def test_invalid_document_extension_rejected(self):
        bad_file = create_test_file(
            name='malicious.exe',
            content=b'MZ fake exe',
            content_type='application/octet-stream'
        )
        response = self.client.post(
            reverse('jeanclaudeirumva:upload_document'),
            {'document': bad_file},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid file')

    def test_document_upload_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('jeanclaudeirumva:upload_document'))
        self.assertEqual(response.status_code, 302)


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

    def test_logout_success(self):
        response = self.client.post(reverse('jeanclaudeirumva:logout'))
        self.assertRedirects(response, reverse('jeanclaudeirumva:login'))