"""
Management command to set up Django groups and permissions for RBAC.

This command creates the following roles:
- Student: Basic access (view own profile, change password)
- Instructor: Extended access (view student profiles, manage submissions)
- Staff: Administrative access (all student management)
- Admin: Full access (all system functions)
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Set up roles (groups) and permissions for the RBAC system'

    def handle(self, *args, **options):
        """Execute the command to create roles and assign permissions."""
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('Setting up Role-Based Access Control (RBAC)'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        # Define roles and their descriptions
        roles = {
            'Student': 'Basic student access - view own profile',
            'Instructor': 'Instructor access - manage student submissions',
            'Staff': 'Staff access - manage users and submissions',
            'Admin': 'Admin access - full system access',
        }

        # Create groups
        created_groups = {}
        for role_name, description in roles.items():
            group, created = Group.objects.get_or_create(name=role_name)
            created_groups[role_name] = group
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS('[+] Created group: {}'.format(role_name))
                )
                self.stdout.write('    Description: {}'.format(description))
            else:
                self.stdout.write(
                    self.style.WARNING('[*] Group already exists: {}'.format(role_name))
                )

        # Get content types for permissions
        from aline.models import UserProfile
        user_profile_ct = ContentType.objects.get_for_model(UserProfile)
        auth_user_ct = ContentType.objects.get_for_model(__import__('django.contrib.auth.models', fromlist=['User']).User)

        # Define permissions for each role
        # We'll use Django's built-in permissions and create custom ones as needed
        permissions_map = {
            'Student': [
                # Students can view own profile
                ('view_userprofile', user_profile_ct, 'Can view user profile'),
            ],
            'Instructor': [
                # Instructors can view all profiles
                ('view_all_userprofiles', user_profile_ct, 'Can view all user profiles'),
            ],
            'Staff': [
                # Staff can add, change, delete user profiles
                ('add_userprofile', user_profile_ct, 'Can add user profile'),
                ('change_userprofile', user_profile_ct, 'Can change user profile'),
                ('delete_userprofile', user_profile_ct, 'Can delete user profile'),
                ('view_all_userprofiles', user_profile_ct, 'Can view all user profiles'),
            ],
            'Admin': [
                # Admin gets all permissions (implicitly through is_staff/is_superuser)
            ],
        }

        # Create and assign permissions
        self.stdout.write(self.style.SUCCESS('\nConfiguring permissions:'))
        
        for role_name, perms in permissions_map.items():
            group = created_groups[role_name]
            self.stdout.write(f'\n{role_name}:')
            
            for perm_data in perms:
                if len(perm_data) == 3:
                    codename, ct, description = perm_data
                    perm, perm_created = Permission.objects.get_or_create(
                        codename=codename,
                        content_type=ct,
                        defaults={'name': description}
                    )
                else:
                    # Use existing permission
                    codename = perm_data
                    try:
                        # Try to get Django's built-in permission
                        perm = Permission.objects.get(codename=codename)
                    except Permission.DoesNotExist:
                        continue

                group.permissions.add(perm)
                self.stdout.write(f'  - {perm.name}')

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('RBAC Setup Complete!'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.WARNING('\nNext steps:'))
        self.stdout.write('1. Assign users to groups via Django admin or manually')
        self.stdout.write('2. Access control is now enforced in views and templates')
        self.stdout.write('3. Run tests to verify authorization is working\n')
