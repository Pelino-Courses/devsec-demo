from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from hirwafab.models import UserProfile
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Set up role-based access control groups and permissions'

    def handle(self, *args, **options):
        # Get content types
        user_profile_ct = ContentType.objects.get_for_model(UserProfile)
        user_ct = ContentType.objects.get_for_model(User)

        # Create custom permissions for UserProfile
        permissions_to_create = [
            ('view_dashboard', 'Can view own dashboard', user_profile_ct),
            ('view_own_profile', 'Can view own profile', user_profile_ct),
            ('change_own_profile', 'Can edit own profile', user_profile_ct),
            ('view_user_directory', 'Can view public user directory', user_profile_ct),
            ('view_all_profiles', 'Can view all user profiles', user_profile_ct),
            ('view_user_activity', 'Can view user activity logs', user_profile_ct),
            ('download_reports', 'Can download user reports', user_profile_ct),
        ]

        # Create custom permission for password change
        permissions_to_create.append(
            ('change_own_password', 'Can change own password', user_ct)
        )

        created_count = 0
        for codename, name, content_type in permissions_to_create:
            perm, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=content_type,
                defaults={'name': name}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Created permission: {codename}'))
                created_count += 1
            else:
                self.stdout.write(self.style.WARNING(f'✓ Permission already exists: {codename}'))

        # Create groups
        students_group, created = Group.objects.get_or_create(name='students')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created group: students'))
        else:
            self.stdout.write(self.style.WARNING('✓ Group already exists: students'))

        instructors_group, created = Group.objects.get_or_create(name='instructors')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created group: instructors'))
        else:
            self.stdout.write(self.style.WARNING('✓ Group already exists: instructors'))

        # Assign permissions to students group
        student_perms = [
            'view_dashboard',
            'view_own_profile',
            'change_own_profile',
            'change_own_password',
            'view_user_directory',
        ]
        for perm_codename in student_perms:
            try:
                perm = Permission.objects.get(codename=perm_codename)
                students_group.permissions.add(perm)
            except Permission.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'✗ Permission not found: {perm_codename}'))

        self.stdout.write(self.style.SUCCESS('✓ Assigned permissions to students group'))

        # Assign permissions to instructors group
        instructor_perms = student_perms + [
            'view_all_profiles',
            'view_user_activity',
            'download_reports',
        ]
        for perm_codename in instructor_perms:
            try:
                perm = Permission.objects.get(codename=perm_codename)
                instructors_group.permissions.add(perm)
            except Permission.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'✗ Permission not found: {perm_codename}'))

        self.stdout.write(self.style.SUCCESS('✓ Assigned permissions to instructors group'))

        self.stdout.write(self.style.SUCCESS('\n✅ RBAC setup complete!'))
        self.stdout.write(self.style.WARNING(
            '\nNote: Assign users to groups via:\n'
            '  - Django admin: /admin/auth/group/\n'
            '  - Or: user.groups.add(students_group)'
        ))
