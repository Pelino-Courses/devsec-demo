from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from .roles import ROLE_STUDENT, ROLE_INSTRUCTOR, ROLE_ADMIN, setup_roles, assign_role, get_user_role


class RoleSetupTestCase(TestCase):
    def test_setup_roles_creates_groups(self):
        setup_roles()
        self.assertTrue(Group.objects.filter(name=ROLE_STUDENT).exists())
        self.assertTrue(Group.objects.filter(name=ROLE_INSTRUCTOR).exists())
        self.assertTrue(Group.objects.filter(name=ROLE_ADMIN).exists())


class RegistrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        setup_roles()

    def test_register_page_loads(self):
        response = self.client.get(reverse('jeanclaudeirumva:register'))
        self.assertEqual(response.status_code, 200)

    def test_register_assigns_student_role(self):
        self.client.post(reverse('jeanclaudeirumva:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        user = User.objects.get(username='newuser')
        self.assertTrue(user.groups.filter(name=ROLE_STUDENT).exists())


class RBACTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        setup_roles()

        self.student = User.objects.create_user(
            username='student', password='StrongPass123!')
        assign_role(self.student, ROLE_STUDENT)

        self.instructor = User.objects.create_user(
            username='instructor', password='StrongPass123!')
        assign_role(self.instructor, ROLE_INSTRUCTOR)

        self.admin = User.objects.create_user(
            username='admin_user', password='StrongPass123!',
            is_staff=True)

    def test_student_cannot_access_instructor_area(self):
        self.client.login(username='student', password='StrongPass123!')
        response = self.client.get(reverse('jeanclaudeirumva:instructor_area'))
        self.assertRedirects(response, reverse('jeanclaudeirumva:dashboard'))

    def test_instructor_can_access_instructor_area(self):
        self.client.login(username='instructor', password='StrongPass123!')
        response = self.client.get(reverse('jeanclaudeirumva:instructor_area'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_instructor_area(self):
        self.client.login(username='admin_user', password='StrongPass123!')
        response = self.client.get(reverse('jeanclaudeirumva:instructor_area'))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_access_admin_area(self):
        self.client.login(username='student', password='StrongPass123!')
        response = self.client.get(reverse('jeanclaudeirumva:admin_area'))
        self.assertRedirects(response, reverse('jeanclaudeirumva:dashboard'))

    def test_instructor_cannot_access_admin_area(self):
        self.client.login(username='instructor', password='StrongPass123!')
        response = self.client.get(reverse('jeanclaudeirumva:admin_area'))
        self.assertRedirects(response, reverse('jeanclaudeirumva:dashboard'))

    def test_admin_can_access_admin_area(self):
        self.client.login(username='admin_user', password='StrongPass123!')
        response = self.client.get(reverse('jeanclaudeirumva:admin_area'))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_cannot_access_instructor_area(self):
        response = self.client.get(reverse('jeanclaudeirumva:instructor_area'))
        self.assertRedirects(response, reverse('jeanclaudeirumva:login'))

    def test_anonymous_cannot_access_admin_area(self):
        response = self.client.get(reverse('jeanclaudeirumva:admin_area'))
        self.assertRedirects(response, reverse('jeanclaudeirumva:login'))

    def test_get_user_role_student(self):
        self.assertEqual(get_user_role(self.student), ROLE_STUDENT)

    def test_get_user_role_instructor(self):
        self.assertEqual(get_user_role(self.instructor), ROLE_INSTRUCTOR)

    def test_get_user_role_admin(self):
        self.assertEqual(get_user_role(self.admin), ROLE_ADMIN)


class ProtectedPagesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        setup_roles()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='StrongPass123!'
        )
        assign_role(self.user, ROLE_STUDENT)

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