"""
Tests for Role-Based Access Control (RBAC) system.

This module provides comprehensive tests for the authorization system,
ensuring that access control rules are correctly enforced for different user roles.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from .models import UserProfile
from .decorators import get_user_role, is_admin, is_staff_or_admin, is_instructor_or_above


class RoleBasedAccessControlTestCase(TestCase):
    """Test cases for RBAC authorization system."""

    @classmethod
    def setUpClass(cls):
        """Set up test groups and users once."""
        super().setUpClass()
        
        # Create groups
        cls.student_group = Group.objects.create(name='Student')
        cls.instructor_group = Group.objects.create(name='Instructor')
        cls.staff_group = Group.objects.create(name='Staff')
        cls.admin_group = Group.objects.create(name='Admin')

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        
        # Create test users with different roles
        self.student_user = User.objects.create_user(
            username='student_user',
            email='student@example.com',
            password='TestPass123!'
        )
        self.student_user.groups.add(self.student_group)
        UserProfile.objects.create(user=self.student_user, student_id='STU001')

        self.instructor_user = User.objects.create_user(
            username='instructor_user',
            email='instructor@example.com',
            password='TestPass123!'
        )
        self.instructor_user.groups.add(self.instructor_group)
        UserProfile.objects.create(user=self.instructor_user, student_id='INST001')

        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@example.com',
            password='TestPass123!'
        )
        self.staff_user.groups.add(self.staff_group)
        UserProfile.objects.create(user=self.staff_user, student_id='STAFF001')

        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='TestPass123!'
        )
        self.admin_user.is_superuser = True
        self.admin_user.is_staff = True
        self.admin_user.save()
        UserProfile.objects.create(user=self.admin_user, student_id='ADMIN001')

    def test_get_user_role_anonymous(self):
        """Test role detection for anonymous users."""
        from django.contrib.auth.models import AnonymousUser
        user = AnonymousUser()
        self.assertEqual(get_user_role(user), 'anonymous')

    def test_get_user_role_student(self):
        """Test role detection for student users."""
        role = get_user_role(self.student_user)
        self.assertEqual(role, 'student')

    def test_get_user_role_instructor(self):
        """Test role detection for instructor users."""
        role = get_user_role(self.instructor_user)
        self.assertEqual(role, 'instructor')

    def test_get_user_role_staff(self):
        """Test role detection for staff users."""
        role = get_user_role(self.staff_user)
        self.assertEqual(role, 'staff')

    def test_get_user_role_admin(self):
        """Test role detection for admin users."""
        role = get_user_role(self.admin_user)
        self.assertEqual(role, 'admin')

    def test_is_admin_function(self):
        """Test admin permission check."""
        self.assertFalse(is_admin(self.student_user))
        self.assertFalse(is_admin(self.instructor_user))
        self.assertFalse(is_admin(self.staff_user))
        self.assertTrue(is_admin(self.admin_user))

    def test_is_staff_or_admin_function(self):
        """Test staff/admin permission check."""
        self.assertFalse(is_staff_or_admin(self.student_user))
        self.assertFalse(is_staff_or_admin(self.instructor_user))
        self.assertTrue(is_staff_or_admin(self.staff_user))
        self.assertTrue(is_staff_or_admin(self.admin_user))

    def test_is_instructor_or_above_function(self):
        """Test instructor/above permission check."""
        self.assertFalse(is_instructor_or_above(self.student_user))
        self.assertTrue(is_instructor_or_above(self.instructor_user))
        self.assertTrue(is_instructor_or_above(self.staff_user))
        self.assertTrue(is_instructor_or_above(self.admin_user))


class AdminViewAccessControlTestCase(TestCase):
    """Test admin view access control."""

    @classmethod
    def setUpClass(cls):
        """Set up test groups."""
        super().setUpClass()
        cls.student_group = Group.objects.create(name='Student')
        cls.staff_group = Group.objects.create(name='Staff')
        cls.admin_group = Group.objects.create(name='Admin')

    def setUp(self):
        """Set up test users."""
        self.client = Client()
        
        self.student_user = User.objects.create_user(
            username='student',
            password='TestPass123!'
        )
        self.student_user.groups.add(self.student_group)
        UserProfile.objects.create(user=self.student_user, student_id='STU001')

        self.staff_user = User.objects.create_user(
            username='staff',
            password='TestPass123!'
        )
        self.staff_user.groups.add(self.staff_group)
        UserProfile.objects.create(user=self.staff_user, student_id='STAFF001')

        self.admin_user = User.objects.create_user(
            username='admin',
            password='TestPass123!'
        )
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()
        UserProfile.objects.create(user=self.admin_user, student_id='ADMIN001')

    def test_anonymous_cannot_access_admin_dashboard(self):
        """Test that anonymous users cannot access admin dashboard."""
        response = self.client.get(reverse('aline:admin_dashboard'))
        self.assertEqual(response.status_code, 302)  # Should redirect to login

    def test_student_cannot_access_admin_dashboard(self):
        """Test that students cannot access admin dashboard."""
        self.client.login(username='student', password='TestPass123!')
        response = self.client.get(reverse('aline:admin_dashboard'))
        self.assertEqual(response.status_code, 403)  # Should return forbidden

    def test_staff_cannot_access_admin_dashboard(self):
        """Test that staff cannot access admin dashboard."""
        self.client.login(username='staff', password='TestPass123!')
        response = self.client.get(reverse('aline:admin_dashboard'))
        self.assertEqual(response.status_code, 403)  # Should return forbidden

    def test_admin_can_access_admin_dashboard(self):
        """Test that admin can access admin dashboard."""
        self.client.login(username='admin', password='TestPass123!')
        response = self.client.get(reverse('aline:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'aline/admin/admin_dashboard.html')


class StaffViewAccessControlTestCase(TestCase):
    """Test staff view access control."""

    @classmethod
    def setUpClass(cls):
        """Set up test groups."""
        super().setUpClass()
        cls.student_group = Group.objects.create(name='Student')
        cls.staff_group = Group.objects.create(name='Staff')

    def setUp(self):
        """Set up test users."""
        self.client = Client()
        
        self.student_user = User.objects.create_user(
            username='student',
            password='TestPass123!'
        )
        self.student_user.groups.add(self.student_group)
        UserProfile.objects.create(user=self.student_user, student_id='STU001')

        self.staff_user = User.objects.create_user(
            username='staff',
            password='TestPass123!'
        )
        self.staff_user.groups.add(self.staff_group)
        UserProfile.objects.create(user=self.staff_user, student_id='STAFF001')

    def test_anonymous_cannot_access_user_management(self):
        """Test that anonymous users cannot access user management."""
        response = self.client.get(reverse('aline:user_management'))
        self.assertEqual(response.status_code, 302)  # Should redirect to login

    def test_student_cannot_access_user_management(self):
        """Test that students cannot access user management."""
        self.client.login(username='student', password='TestPass123!')
        response = self.client.get(reverse('aline:user_management'))
        self.assertEqual(response.status_code, 403)  # Should return forbidden

    def test_staff_can_access_user_management(self):
        """Test that staff can access user management."""
        self.client.login(username='staff', password='TestPass123!')
        response = self.client.get(reverse('aline:user_management'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'aline/admin/user_management.html')


class InstructorViewAccessControlTestCase(TestCase):
    """Test instructor view access control."""

    @classmethod
    def setUpClass(cls):
        """Set up test groups."""
        super().setUpClass()
        cls.student_group = Group.objects.create(name='Student')
        cls.instructor_group = Group.objects.create(name='Instructor')

    def setUp(self):
        """Set up test users."""
        self.client = Client()
        
        self.student_user = User.objects.create_user(
            username='student',
            password='TestPass123!'
        )
        self.student_user.groups.add(self.student_group)
        UserProfile.objects.create(user=self.student_user, student_id='STU001')

        self.instructor_user = User.objects.create_user(
            username='instructor',
            password='TestPass123!'
        )
        self.instructor_user.groups.add(self.instructor_group)
        UserProfile.objects.create(user=self.instructor_user, student_id='INST001')

    def test_anonymous_cannot_access_student_list(self):
        """Test that anonymous users cannot access student list."""
        response = self.client.get(reverse('aline:student_list'))
        self.assertEqual(response.status_code, 302)  # Should redirect to login

    def test_student_cannot_access_student_list(self):
        """Test that students cannot access student list."""
        self.client.login(username='student', password='TestPass123!')
        response = self.client.get(reverse('aline:student_list'))
        self.assertEqual(response.status_code, 403)  # Should return forbidden

    def test_instructor_can_access_student_list(self):
        """Test that instructors can access student list."""
        self.client.login(username='instructor', password='TestPass123!')
        response = self.client.get(reverse('aline:student_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'aline/instructor/student_list.html')


class UnauthorizedAccessAttemptTestCase(TestCase):
    """Test handling of unauthorized access attempts."""

    @classmethod
    def setUpClass(cls):
        """Set up test groups."""
        super().setUpClass()
        cls.student_group = Group.objects.create(name='Student')

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        
        self.student_user = User.objects.create_user(
            username='student',
            password='TestPass123!'
        )
        self.student_user.groups.add(self.student_group)
        UserProfile.objects.create(user=self.student_user, student_id='STU001')

    def test_unauthorized_access_returns_403(self):
        """Test that unauthorized access returns HTTP 403."""
        self.client.login(username='student', password='TestPass123!')
        response = self.client.get(reverse('aline:admin_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_access_redirects_to_login(self):
        """Test that unauthenticated access redirects to login."""
        response = self.client.get(reverse('aline:admin_dashboard'), follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)


class RoleBasedViewContextTestCase(TestCase):
    """Test that views provide role information in context."""

    def test_dashboard_includes_role_info(self):
        """Test that dashboard view includes role information."""
        student = User.objects.create_user(
            username='student',
            password='TestPass123!'
        )
        student_group = Group.objects.create(name='Student')
        student.groups.add(student_group)
        UserProfile.objects.create(user=student, student_id='STU001')
        
        self.client.login(username='student', password='TestPass123!')
        response = self.client.get(reverse('aline:dashboard'))
        
        self.assertIn('user_role', response.context)
        self.assertIn('is_admin', response.context)
        self.assertIn('is_staff', response.context)
        self.assertIn('is_instructor', response.context)
        self.assertEqual(response.context['user_role'], 'student')
