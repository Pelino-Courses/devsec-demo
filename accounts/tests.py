from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import UserProfile

class CSRFTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        UserProfile.objects.create(user=self.user)
        self.client = Client(enforce_csrf_checks=True)
        self.client.login(username='testuser', password='password123')
        self.url = reverse('update_display_name')

    def test_ajax_update_fails_without_csrf(self):
        """Verify that a POST request without a CSRF token fails with 403."""
        response = self.client.post(self.url, {'display_name': 'New Name'})
        self.assertEqual(response.status_code, 403)

    def test_ajax_update_succeeds_with_csrf(self):
        """Verify that a POST request with a CSRF token succeeds."""
        # Get a token first
        self.client.get(reverse('profile'))
        csrf_token = self.client.cookies['csrftoken'].value
        
        response = self.client.post(
            self.url, 
            {'display_name': 'New Name'},
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['display_name'], 'New Name')
        
        # Verify database update
        self.user.userprofile.refresh_from_db()
        self.assertEqual(self.user.userprofile.display_name, 'New Name')
