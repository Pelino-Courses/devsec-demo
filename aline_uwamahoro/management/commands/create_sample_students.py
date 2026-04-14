"""
Management command to create sample student users for demonstration.

This command creates 4 test students with the default password 'user@123'.
Useful for development and testing purposes.

Usage:
    python manage.py create_sample_students
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from aline_uwamahoro.models import UserProfile


class Command(BaseCommand):
    """Create sample student data for testing."""
    
    help = 'Creates 4 sample student accounts with default password'
    
    def add_arguments(self, parser):
        """Add command-line arguments."""
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete existing sample students before creating new ones',
        )
    
    def handle(self, *args, **options):
        """Execute the command."""
        default_password = 'user@123'
        
        sample_students = [
            {
                'username': 'student1',
                'email': 'student1@example.com',
                'first_name': 'Alice',
                'last_name': 'Johnson',
                'student_id': 'STU001',
            },
            {
                'username': 'student2',
                'email': 'student2@example.com',
                'first_name': 'Bob',
                'last_name': 'Smith',
                'student_id': 'STU002',
            },
            {
                'username': 'student3',
                'email': 'student3@example.com',
                'first_name': 'Carol',
                'last_name': 'Williams',
                'student_id': 'STU003',
            },
            {
                'username': 'student4',
                'email': 'student4@example.com',
                'first_name': 'David',
                'last_name': 'Brown',
                'student_id': 'STU004',
            },
        ]
        
        # Optionally delete existing sample students
        if options['delete']:
            student_ids = [s['student_id'] for s in sample_students]
            deleted_count, _ = UserProfile.objects.filter(
                student_id__in=student_ids
            ).delete()
            self.stdout.write(
                self.style.SUCCESS(f'Deleted {deleted_count} sample students')
            )
        
        created_count = 0
        skipped_count = 0
        
        for student_data in sample_students:
            username = student_data['username']
            
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"User '{username}' already exists, skipping..."
                    )
                )
                skipped_count += 1
                continue
            
            # Create user
            user = User.objects.create_user(
                username=username,
                email=student_data['email'],
                password=default_password,
                first_name=student_data['first_name'],
                last_name=student_data['last_name'],
            )
            
            # Create associated UserProfile
            UserProfile.objects.create(
                user=user,
                student_id=student_data['student_id'],
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Created student: {username} "
                    f"({student_data['first_name']} {student_data['last_name']})"
                )
            )
            created_count += 1
        
        # Print summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'=' * 60}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Sample Data Creation Complete!\n'
            )
        )
        self.stdout.write(
            f'Created: {created_count} students\n'
            f'Skipped: {skipped_count} students (already exist)\n'
            f'Total: {created_count + skipped_count} students'
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'=' * 60}"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                f'\nDefault password for all accounts: {default_password}\n'
            )
        )
        self.stdout.write(
            'Test accounts:\n'
        )
        for student in sample_students[:created_count]:
            self.stdout.write(f"  • {student['username']}")
        self.stdout.write('\nVisit: http://localhost:8000/login/\n')
