from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User


# Role names
ROLE_STUDENT = 'student'
ROLE_INSTRUCTOR = 'instructor'
ROLE_ADMIN = 'admin'


def setup_roles():
    """
    Create default groups and permissions.
    Call this once during setup or migrations.
    """
    # Create groups
    student_group, _ = Group.objects.get_or_create(name=ROLE_STUDENT)
    instructor_group, _ = Group.objects.get_or_create(name=ROLE_INSTRUCTOR)
    admin_group, _ = Group.objects.get_or_create(name=ROLE_ADMIN)

    return student_group, instructor_group, admin_group


def assign_role(user, role_name):
    """Assign a role to a user."""
    group = Group.objects.get(name=role_name)
    user.groups.add(group)


def remove_role(user, role_name):
    """Remove a role from a user."""
    group = Group.objects.get(name=role_name)
    user.groups.remove(group)


def get_user_role(user):
    """Get the primary role of a user."""
    if user.is_superuser or user.is_staff:
        return ROLE_ADMIN
    groups = user.groups.values_list('name', flat=True)
    if ROLE_INSTRUCTOR in groups:
        return ROLE_INSTRUCTOR
    if ROLE_STUDENT in groups:
        return ROLE_STUDENT
    return None


def is_student(user):
    return user.groups.filter(name=ROLE_STUDENT).exists()


def is_instructor(user):
    return user.groups.filter(name=ROLE_INSTRUCTOR).exists() or user.is_staff


def is_admin(user):
    return user.is_superuser or user.is_staff