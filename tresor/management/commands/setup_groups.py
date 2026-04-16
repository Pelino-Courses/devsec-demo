from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from tresor.models import Profile


class Command(BaseCommand):
    help = 'Create default groups and permissions for RBAC'

    def handle(self, *args, **options):
        profile_ct = ContentType.objects.get_for_model(Profile)

        view_profile_perm, _ = Permission.objects.get_or_create(
            codename='view_all_profiles',
            content_type=profile_ct,
            defaults={'name': 'Can view all profiles'},
        )

        instructor_group, created = Group.objects.get_or_create(name='instructor')
        instructor_group.permissions.set([view_profile_perm])

        Group.objects.get_or_create(name='student')

        if created:
            self.stdout.write(self.style.SUCCESS('Groups created successfully.'))
        else:
            self.stdout.write(self.style.SUCCESS('Groups already exist.'))
