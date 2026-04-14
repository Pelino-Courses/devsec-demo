"""
Management command to set up role-based access control groups and permissions.
This command creates:
- Student group (authenticated users with basic access)
- Instructor group (staff users with teaching/audit access)
- Admin group (superusers with full access)

Run with: python manage.py setup_rbac_groups
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from antoine.models import UserProfile, LoginHistory, PasswordChangeHistory


class Command(BaseCommand):
    help = 'Set up role-based access control groups and permissions for UAS'

    def handle(self, *args, **options):
        self.stdout.write('Setting up RBAC groups and permissions...')

        # Get content types
        user_profile_ct = ContentType.objects.get_for_model(UserProfile)
        login_history_ct = ContentType.objects.get_for_model(LoginHistory)
        password_history_ct = ContentType.objects.get_for_model(PasswordChangeHistory)

        # Get or create permissions
        can_view_all_users, _ = Permission.objects.get_or_create(
            codename='view_all_users_profile',
            name='Can view all user profiles',
            content_type=user_profile_ct,
        )

        can_view_audit_logs, _ = Permission.objects.get_or_create(
            codename='view_audit_logs',
            name='Can view all login and password audit logs',
            content_type=login_history_ct,
        )

        can_reset_password, _ = Permission.objects.get_or_create(
            codename='reset_user_password',
            name='Can reset other users passwords',
            content_type=user_profile_ct,
        )

        can_manage_users, _ = Permission.objects.get_or_create(
            codename='manage_all_users',
            name='Can manage all users and groups',
            content_type=user_profile_ct,
        )

        # Create or get Student group
        student_group, created = Group.objects.get_or_create(name='Student')
        if created:
            self.stdout.write(
                self.style.SUCCESS('✓ Created Student group')
            )
        # Students have no special permissions - just standard auth

        # Create or get Instructor group
        instructor_group, created = Group.objects.get_or_create(name='Instructor')
        if created:
            self.stdout.write(
                self.style.SUCCESS('✓ Created Instructor group')
            )
        # Add instructor permissions
        instructor_group.permissions.set([
            can_view_all_users,
            can_view_audit_logs,
            can_reset_password,
        ])
        self.stdout.write(
            self.style.SUCCESS('✓ Instructor permissions: view_all_users, view_audit_logs, reset_password')
        )

        # Create or get Admin group
        admin_group, created = Group.objects.get_or_create(name='Admin')
        if created:
            self.stdout.write(
                self.style.SUCCESS('✓ Created Admin group')
            )
        # Add admin permissions (all permissions)
        admin_group.permissions.set([
            can_view_all_users,
            can_view_audit_logs,
            can_reset_password,
            can_manage_users,
        ])
        self.stdout.write(
            self.style.SUCCESS('✓ Admin permissions: all permissions enabled')
        )

        self.stdout.write(
            self.style.SUCCESS(
                '\n✅ RBAC setup complete!\n'
                'Groups created:\n'
                '  - Student: Basic authenticated access\n'
                '  - Instructor: Staff access with audit viewing\n'
                '  - Admin: Full administrative access\n'
            )
        )
