from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from uwamahoro_joseline.models import Profile

INSTRUCTOR_PERMISSIONS = [
    "can_view_all_profiles",
    "can_manage_users",
]


class Command(BaseCommand):
    help = "Create the Instructor group and assign its permissions. Optionally promote a user."

    def add_arguments(self, parser):
        parser.add_argument(
            "--promote",
            metavar="USERNAME",
            help="Username of the user to promote to Instructor after setup",
        )

    def handle(self, *args, **options):
        content_type = ContentType.objects.get_for_model(Profile)

        permissions = []
        for codename in INSTRUCTOR_PERMISSIONS:
            perm = Permission.objects.filter(
                codename=codename, content_type=content_type
            ).first()
            if perm is None:
                self.stderr.write(
                    f"Permission '{codename}' not found. Run 'migrate' first."
                )
                return
            permissions.append(perm)

        group, created = Group.objects.get_or_create(name="Instructor")
        group.permissions.set(permissions)

        if created:
            self.stdout.write(self.style.SUCCESS("Created 'Instructor' group with permissions:"))
        else:
            self.stdout.write(self.style.WARNING("'Instructor' group already exists — permissions refreshed:"))

        for perm in permissions:
            self.stdout.write(f"  + {perm.codename}")

        if options["promote"]:
            username = options["promote"]
            try:
                user = User.objects.get(username=username)
                user.groups.add(group)
                self.stdout.write(self.style.SUCCESS(f"Promoted '{username}' to Instructor."))
            except User.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"User '{username}' not found."))
