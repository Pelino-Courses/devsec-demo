from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from uwamahoro_joseline.models import Profile

DEFAULT_PASSWORD = "pass@123"

SAMPLE_USERS = [
    {"username": "mutesi_claudine", "first_name": "Claudine", "last_name": "Mutesi", "email": "claudine.mutesi@example.rw"},
    {"username": "niyonkuru_jean", "first_name": "Jean", "last_name": "Niyonkuru", "email": "jean.niyonkuru@example.rw"},
    {"username": "uwimana_marie", "first_name": "Marie", "last_name": "Uwimana", "email": "marie.uwimana@example.rw"},
    {"username": "habimana_patrick", "first_name": "Patrick", "last_name": "Habimana", "email": "patrick.habimana@example.rw"},
    {"username": "mukamana_solange", "first_name": "Solange", "last_name": "Mukamana", "email": "solange.mukamana@example.rw"},
    {"username": "nshimiyimana_eric", "first_name": "Eric", "last_name": "Nshimiyimana", "email": "eric.nshimiyimana@example.rw"},
    {"username": "uwineza_jacqueline", "first_name": "Jacqueline", "last_name": "Uwineza", "email": "jacqueline.uwineza@example.rw"},
    {"username": "bizimana_thomas", "first_name": "Thomas", "last_name": "Bizimana", "email": "thomas.bizimana@example.rw"},
    {"username": "mukandutiye_celestine", "first_name": "Celestine", "last_name": "Mukandutiye", "email": "celestine.mukandutiye@example.rw"},
    {"username": "ndayishimiye_joseph", "first_name": "Joseph", "last_name": "Ndayishimiye", "email": "joseph.ndayishimiye@example.rw"},
]


class Command(BaseCommand):
    help = "Seed the database with 10 sample users using Kinyarwanda names"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing seed users before re-creating them",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            usernames = [u["username"] for u in SAMPLE_USERS]
            deleted, _ = User.objects.filter(username__in=usernames).delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing seed user(s)."))

        created_count = 0
        skipped_count = 0

        for data in SAMPLE_USERS:
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "email": data["email"],
                },
            )
            if created:
                user.set_password(DEFAULT_PASSWORD)
                user.save()
                Profile.objects.get_or_create(user=user)
                self.stdout.write(
                    self.style.SUCCESS(f"  [created] {user.username} ({user.get_full_name()})")
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f"  [skipped] {user.username} already exists")
                )
                skipped_count += 1

        self.stdout.write("")
        self.stdout.write(f"Done. Created: {created_count}  Skipped: {skipped_count}")
        if created_count:
            self.stdout.write(f"Default password for all new users: {DEFAULT_PASSWORD}")
