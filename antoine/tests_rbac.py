"""
Tests for Role-Based Access Control (RBAC) in the UAS.
Tests verify that users can only access resources appropriate for their role.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from antoine.models import UserProfile, LoginHistory, PasswordChangeHistory
from antoine.permissions import get_user_role, has_permission, is_admin, is_instructor


class RBACGroupSetupTest(TestCase):
    """Test that RBAC groups and permissions exist"""

    def setUp(self):
        """Create test groups and permissions"""
        # Create groups
        self.student_group = Group.objects.create(name='Student')
        self.instructor_group = Group.objects.create(name='Instructor')
        self.admin_group = Group.objects.create(name='Admin')
        
        # Create permissions
        user_profile_ct = ContentType.objects.get_for_model(UserProfile)
        self.view_all_users_perm = Permission.objects.create(
            codename='view_all_users_profile',
            name='Can view all user profiles',
            content_type=user_profile_ct,
        )
        self.view_audit_logs_perm = Permission.objects.create(
            codename='view_audit_logs',
            name='Can view audit logs',
            content_type=user_profile_ct,
        )
        self.manage_all_perm = Permission.objects.create(
            codename='manage_all_users',
            name='Can manage all users',
            content_type=user_profile_ct,
        )

    def test_groups_exist(self):
        """Test that required groups are created"""
        self.assertTrue(Group.objects.filter(name='Student').exists())
        self.assertTrue(Group.objects.filter(name='Instructor').exists())
        self.assertTrue(Group.objects.filter(name='Admin').exists())

    def test_permissions_exist(self):
        """Test that required permissions are created"""
        self.assertTrue(
            Permission.objects.filter(codename='view_all_users_profile').exists()
        )
        self.assertTrue(
            Permission.objects.filter(codename='view_audit_logs').exists()
        )
        self.assertTrue(
            Permission.objects.filter(codename='manage_all_users').exists()
        )


class UserRoleDeterminationTest(TestCase):
    """Test get_user_role() function for different users"""

    def setUp(self):
        """Create test users with different roles"""
        # Create groups
        self.student_group = Group.objects.create(name='Student')
        self.instructor_group = Group.objects.create(name='Instructor')
        self.admin_group = Group.objects.create(name='Admin')
        
        # Create users
        self.anonymous_user = User(username='anonymous')
        
        self.student = User.objects.create_user(
            username='student1',
            password='testpass123'
        )
        self.student.groups.add(self.student_group)
        
        self.instructor = User.objects.create_user(
            username='instructor1',
            password='testpass123'
        )
        self.instructor.groups.add(self.instructor_group)
        
        self.admin = User.objects.create_user(
            username='admin1',
            password='testpass123',
            is_superuser=True
        )
        self.admin.groups.add(self.admin_group)

    def test_get_role_anonymous(self):
        """Test get_user_role returns 'anonymous' for unauthenticated user"""
        role = get_user_role(self.anonymous_user)
        self.assertEqual(role, 'anonymous')

    def test_get_role_student(self):
        """Test get_user_role returns 'student' for student group member"""
        role = get_user_role(self.student)
        self.assertEqual(role, 'student')

    def test_get_role_instructor(self):
        """Test get_user_role returns 'instructor' for instructor group member"""
        role = get_user_role(self.instructor)
        self.assertEqual(role, 'instructor')

    def test_get_role_admin(self):
        """Test get_user_role returns 'admin' for superuser"""
        role = get_user_role(self.admin)
        self.assertEqual(role, 'admin')


class PermissionCheckTest(TestCase):
    """Test permission checking functions"""

    def setUp(self):
        """Create test users and permissions"""
        # Create groups
        self.student_group = Group.objects.create(name='Student')
        self.instructor_group = Group.objects.create(name='Instructor')
        
        # Create permissions
        user_profile_ct = ContentType.objects.get_for_model(UserProfile)
        self.view_audit_perm = Permission.objects.create(
            codename='view_audit_logs',
            name='Can view audit logs',
            content_type=user_profile_ct,
        )
        
        # Create users
        self.student = User.objects.create_user(
            username='student1',
            password='testpass123'
        )
        self.student.groups.add(self.student_group)
        
        self.instructor = User.objects.create_user(
            username='instructor1',
            password='testpass123'
        )
        self.instructor.groups.add(self.instructor_group)
        self.instructor.user_permissions.add(self.view_audit_perm)

    def test_student_no_audit_permission(self):
        """Test student cannot view audit logs"""
        self.assertFalse(has_permission(self.student, 'view_audit_logs'))

    def test_instructor_has_audit_permission(self):
        """Test instructor can view audit logs"""
        self.assertTrue(has_permission(self.instructor, 'view_audit_logs'))

    def test_unauthenticated_no_permission(self):
        """Test unauthenticated user has no permissions"""
        anonymous = User(username='anonymous')
        self.assertFalse(has_permission(anonymous, 'view_audit_logs'))


class AnonymousUserAccessTest(TestCase):
    """Test anonymous user access restrictions"""

    def setUp(self):
        self.client = Client()

    def test_anonymous_can_register(self):
        """Test anonymous users can access registration page"""
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/register.html')

    def test_anonymous_can_login(self):
        """Test anonymous users can access login page"""
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/login.html')

    def test_anonymous_cannot_access_dashboard(self):
        """Test anonymous users cannot access dashboard"""
        response = self.client.get('/dashboard/', follow=True)
        self.assertTemplateUsed(response, 'antoine/login.html')

    def test_anonymous_cannot_manage_users(self):
        """Test anonymous users cannot access manage users page"""
        response = self.client.get('/manage-users/', follow=True)
        self.assertTemplateUsed(response, 'antoine/login.html')

    def test_anonymous_cannot_view_audit_logs(self):
        """Test anonymous users cannot access audit logs"""
        response = self.client.get('/audit-logs/', follow=True)
        self.assertTemplateUsed(response, 'antoine/login.html')


class StudentAccessTest(TestCase):
    """Test student (authenticated non-privileged user) access"""

    def setUp(self):
        """Create student user and login"""
        self.client = Client()
        self.student = User.objects.create_user(
            username='student1',
            password='testpass123'
        )
        student_group = Group.objects.create(name='Student')
        self.student.groups.add(student_group)
        self.client.login(username='student1', password='testpass123')

    def test_student_can_access_dashboard(self):
        """Test student can access their dashboard"""
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/dashboard.html')

    def test_student_can_access_profile(self):
        """Test student can access their profile"""
        response = self.client.get('/profile/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/profile.html')

    def test_student_can_change_password(self):
        """Test student can access password change"""
        response = self.client.get('/change-password/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/change_password.html')

    def test_student_can_view_login_history(self):
        """Test student can view their own login history"""
        response = self.client.get('/login-history/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/login_history.html')

    def test_student_cannot_manage_users(self):
        """Test student cannot access manage users"""
        response = self.client.get('/manage-users/')
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertIn('/dashboard/', response.url)

    def test_student_cannot_view_audit_logs(self):
        """Test student cannot access audit logs"""
        response = self.client.get('/audit-logs/')
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertIn('/dashboard/', response.url)


class InstructorAccessTest(TestCase):
    """Test instructor access privileges"""

    def setUp(self):
        """Create instructor user with permissions"""
        self.client = Client()
        
        # Create instructor user
        self.instructor = User.objects.create_user(
            username='instructor1',
            password='testpass123'
        )
        self.instructor_group = Group.objects.create(name='Instructor')
        self.instructor.groups.add(self.instructor_group)
        
        # Add permissions to instructor group
        user_profile_ct = ContentType.objects.get_for_model(UserProfile)
        view_all_perm = Permission.objects.create(
            codename='view_all_users_profile',
            name='Can view all users',
            content_type=user_profile_ct,
        )
        view_audit_perm = Permission.objects.create(
            codename='view_audit_logs',
            name='Can view audit logs',
            content_type=user_profile_ct,
        )
        self.instructor_group.permissions.add(view_all_perm, view_audit_perm)
        
        self.client.login(username='instructor1', password='testpass123')

    def test_instructor_can_access_manage_users(self):
        """Test instructor can access user management"""
        response = self.client.get('/manage-users/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/manage_users.html')

    def test_instructor_can_access_audit_logs(self):
        """Test instructor can view audit logs"""
        response = self.client.get('/audit-logs/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/audit_logs.html')

    def test_instructor_cannot_reset_password(self):
        """Test instructor cannot reset user passwords without Admin permission"""
        # Create another user
        other_user = User.objects.create_user(
            username='other',
            password='testpass123'
        )
        
        response = self.client.post(
            f'/reset-password/{other_user.id}/',
            follow=True
        )
        # Should be redirected (not admin)
        self.assertEqual(response.status_code, 200)
        # Should not have reset the password
        self.assertTrue(other_user.check_password('testpass123'))


class AdminAccessTest(TestCase):
    """Test admin user access privileges"""

    def setUp(self):
        """Create admin/superuser"""
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin1',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        admin_group = Group.objects.create(name='Admin')
        self.admin.groups.add(admin_group)
        self.client.login(username='admin1', password='testpass123')

    def test_admin_can_manage_users(self):
        """Test admin can access user management"""
        response = self.client.get('/manage-users/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/manage_users.html')

    def test_admin_can_view_audit_logs(self):
        """Test admin can view audit logs"""
        response = self.client.get('/audit-logs/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/audit_logs.html')

    def test_admin_can_reset_password(self):
        """Test admin can reset user passwords"""
        # Create another user
        other_user = User.objects.create_user(
            username='other',
            password='oldpass123'
        )
        
        response = self.client.post(
            f'/reset-password/{other_user.id}/',
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify password was reset (old password no longer works)
        other_user.refresh_from_db()
        self.assertFalse(other_user.check_password('oldpass123'))


class UnauthorizedAccessHandlingTest(TestCase):
    """Test that unauthorized access is handled safely"""

    def setUp(self):
        """Create test users"""
        self.client = Client()
        
        # Create student
        self.student = User.objects.create_user(
            username='student1',
            password='testpass123'
        )
        student_group = Group.objects.create(name='Student')
        self.student.groups.add(student_group)
        
        # Create other user
        self.other_user = User.objects.create_user(
            username='other',
            password='testpass123'
        )
        self.other_user.groups.add(student_group)
        
        self.client.login(username='student1', password='testpass123')

    def test_unauthorized_redirect_safe(self):
        """Test unauthorized access redirects safely"""
        response = self.client.get('/manage-users/', follow=True)
        self.assertEqual(response.status_code, 200)
        # Should redirect to safe location (dashboard)
        self.assertTemplateUsed(response, 'antoine/dashboard.html')

    def test_no_sensitive_data_in_error(self):
        """Test error messages don't leak sensitive information"""
        response = self.client.get('/audit-logs/', follow=True)
        # Should not expose internal details
        content = response.content.decode()
        self.assertNotIn('Permission denied', content)  # Generic message only

    def test_access_denied_message_generic(self):
        """Test that access denied messages are generic"""
        # Trying to access admin page as student
        response = self.client.get('/manage-users/')
        # Should be redirected with generic message
        messages_list = list(response.context['messages']) if response.context else []
        for message in messages_list:
            # Message should be generic, not reveal what permission was checked
            self.assertIn('permission', str(message).lower())
