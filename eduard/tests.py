from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.models import Group


class RegistrationTests(TestCase):
    def test_register_page_loads(self):
        response = self.client.get(reverse('eduard:register'))
        self.assertEqual(response.status_code, 200)

    def test_successful_registration(self):
        response = self.client.post(reverse('eduard:register'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertRedirects(response, reverse('eduard:dashboard'))
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_duplicate_email_rejected(self):
        User.objects.create_user(username='existing', email='dupe@example.com', password='pass')
        response = self.client.post(reverse('eduard:register'), {
            'username': 'newuser',
            'email': 'dupe@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'email', 'A user with this email already exists.')

    def test_password_mismatch_rejected(self):
        response = self.client.post(reverse('eduard:register'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'StrongPass123!',
            'password2': 'WrongPass999!',
        })
        self.assertEqual(response.status_code, 200)


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='loginuser', password='TestPass123!')

    def test_login_page_loads(self):
        response = self.client.get(reverse('eduard:login'))
        self.assertEqual(response.status_code, 200)

    def test_successful_login(self):
        response = self.client.post(reverse('eduard:login'), {
            'username': 'loginuser',
            'password': 'TestPass123!',
        })
        self.assertRedirects(response, reverse('eduard:dashboard'))

    def test_wrong_password_rejected(self):
        response = self.client.post(reverse('eduard:login'), {
            'username': 'loginuser',
            'password': 'WrongPassword!',
        })
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        self.client.login(username='loginuser', password='TestPass123!')
        response = self.client.post(reverse('eduard:logout'))
        self.assertRedirects(response, reverse('eduard:login'))


class ProtectedViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='authuser', password='TestPass123!')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('eduard:dashboard'))
        self.assertRedirects(response, f"{reverse('eduard:login')}?next={reverse('eduard:dashboard')}")

    def test_profile_requires_login(self):
        response = self.client.get(reverse('eduard:profile'))
        self.assertRedirects(response, f"{reverse('eduard:login')}?next={reverse('eduard:profile')}")

    def test_authenticated_user_sees_dashboard(self):
        self.client.login(username='authuser', password='TestPass123!')
        response = self.client.get(reverse('eduard:dashboard'))
        self.assertEqual(response.status_code, 200)


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='passuser', password='OldPass123!')
        self.client.login(username='passuser', password='OldPass123!')

    def test_change_password_success(self):
        response = self.client.post(reverse('eduard:change_password'), {
            'old_password': 'OldPass123!',
            'new_password1': 'NewPass456!',
            'new_password2': 'NewPass456!',
        })
        self.assertRedirects(response, reverse('eduard:profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass456!'))



class InstructorAccessTests(TestCase):
    def setUp(self):
        self.instructor_group, _ = Group.objects.get_or_create(name='Instructor')
        self.normal_user = User.objects.create_user(
            username='normal', password='TestPass123!'
        )
        self.instructor_user = User.objects.create_user(
            username='instructor', password='TestPass123!'
        )
        self.instructor_user.groups.add(self.instructor_group)
        self.staff_user = User.objects.create_user(
            username='staffuser', password='TestPass123!', is_staff=True
        )

    def test_anonymous_redirected_from_instructor_page(self):
        response = self.client.get(reverse('eduard:instructor_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_normal_user_gets_403_on_instructor_page(self):
        self.client.login(username='normal', password='TestPass123!')
        response = self.client.get(reverse('eduard:instructor_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_instructor_can_access_instructor_page(self):
        self.client.login(username='instructor', password='TestPass123!')
        response = self.client.get(reverse('eduard:instructor_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_access_instructor_page(self):
        self.client.login(username='staffuser', password='TestPass123!')
        response = self.client.get(reverse('eduard:instructor_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_instructor_page_shows_user_list(self):
        self.client.login(username='instructor', password='TestPass123!')
        response = self.client.get(reverse('eduard:instructor_dashboard'))
        self.assertContains(response, 'normal')