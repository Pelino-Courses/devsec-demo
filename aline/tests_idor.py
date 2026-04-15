"""
Tests for Insecure Direct Object Reference (IDOR) and Privilege Escalation prevention.

This module ensures that users cannot access or modify resources that do not belong to them,
even if they guess or manipulate identifiers in URLs.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from .models import UserProfile
from .decorators import is_admin, is_staff_or_admin


class IDORPreventionTestCase(TestCase):
    """Test cases for IDOR and privilege escalation prevention."""

    @classmethod
    def setUpClass(cls):
        """Set up test groups once."""
        super().setUpClass()
        cls.student_group = Group.objects.create(name='Student')
        cls.staff_group = Group.objects.create(name='Staff')
        cls.admin_group = Group.objects.create(name='Admin')

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        
        # Create a student user
        self.student1 = User.objects.create_user(
            username='student1',
            password='TestPass123!'
        )
        self.student1.groups.add(self.student_group)
        UserProfile.objects.create(user=self.student1, student_id='STU001')

        # Create another student user
        self.student2 = User.objects.create_user(
            username='student2',
            password='TestPass123!'
        )
        self.student2.groups.add(self.student_group)
        UserProfile.objects.create(user=self.student2, student_id='STU002')

        # Create a staff user
        self.staff_user = User.objects.create_user(
            username='staff_user',
            password='TestPass123!'
        )
        self.staff_user.groups.add(self.staff_group)
        UserProfile.objects.create(user=self.staff_user, student_id='STAFF001')

        # Create an admin user
        self.admin_user = User.objects.create_user(
            username='admin_user',
            password='TestPass123!'
        )
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()
        UserProfile.objects.create(user=self.admin_user, student_id='ADMIN001')

    def test_student_cannot_access_other_student_detail(self):
        """Test that a student cannot access another student's detail page (IDOR)."""
        self.client.login(username='student1', password='TestPass123!')
        # Even if they use their own ID, it should be 403 because it's a staff view
        response = self.client.get(reverse('aline:user_detail', kwargs={'user_id': self.student1.id}))
        self.assertEqual(response.status_code, 403)
        
        # Accessing another student's ID should also be 403
        response = self.client.get(reverse('aline:user_detail', kwargs={'user_id': self.student2.id}))
        self.assertEqual(response.status_code, 403)

    def test_staff_cannot_modify_admin_user(self):
        """Test that a staff user (not admin) cannot modify an admin user (IDOR/Privilege Escalation)."""
        self.client.login(username='staff_user', password='TestPass123!')
        
        # Attempt to remove admin from all groups
        response = self.client.post(
            reverse('aline:user_detail', kwargs={'user_id': self.admin_user.id}),
            {'groups': []}
        )
        self.assertEqual(response.status_code, 403)
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.groups.filter(name='Admin').exists() or self.admin_user.is_superuser)

    def test_staff_cannot_assign_privileged_roles(self):
        """Test that a staff user cannot promote themselves or others to Admin status."""
        self.client.login(username='staff_user', password='TestPass123!')
        
        # Attempt to add student2 to Admin group
        response = self.client.post(
            reverse('aline:user_detail', kwargs={'user_id': self.student2.id}),
            {'groups': [self.admin_group.id]}
        )
        self.assertEqual(response.status_code, 403)
        self.student2.refresh_from_db()
        self.assertFalse(self.student2.groups.filter(name='Admin').exists())

    def test_admin_can_modify_any_user(self):
        """Test that admins still have legitimate access to manage all users."""
        self.client.login(username='admin_user', password='TestPass123!')
        
        # Admin changes student2 to Instructor
        response = self.client.post(
            reverse('aline:user_detail', kwargs={'user_id': self.student2.id}),
            {'groups': [self.instructor_group.id if hasattr(self, 'instructor_group') else self.admin_group.id]}
        )
        # Note: I haven't defined instructor_group in this test's setUpClass, let's just use Staff group for test
        response = self.client.post(
            reverse('aline:user_detail', kwargs={'user_id': self.student2.id}),
            {'groups': [self.staff_group.id]}
        )
        self.assertEqual(response.status_code, 302) # Redirects to user detail
        self.student2.refresh_from_db()
        self.assertTrue(self.student2.groups.filter(name='Staff').exists())

    def test_profile_view_is_consistent_and_safe(self):
        """Ensure profile view doesn't accept an ID and only shows current user."""
        self.client.login(username='student1', password='TestPass123!')
        response = self.client.get(reverse('aline:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'].username, 'student1')
