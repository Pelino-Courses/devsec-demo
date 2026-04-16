from django.contrib.auth.models import Group, Permission

INSTRUCTOR_GROUP_NAME = "instructors"
STUDENT_GROUP_NAME = "students"
PRIVILEGED_PERMISSION = "igihozo.view_privileged_dashboard"


def ensure_role_groups():
    students_group, _ = Group.objects.get_or_create(name=STUDENT_GROUP_NAME)
    instructors_group, _ = Group.objects.get_or_create(name=INSTRUCTOR_GROUP_NAME)

    permission = Permission.objects.filter(
        content_type__app_label="igihozo",
        codename="view_privileged_dashboard",
    ).first()
    if permission:
        instructors_group.permissions.add(permission)

    return students_group, instructors_group


def assign_default_role(user):
    students_group, _ = ensure_role_groups()
    if not user.is_superuser and not user.is_staff:
        user.groups.add(students_group)


def user_is_privileged(user):
    if not user.is_authenticated:
        return False
    return user.is_staff or user.is_superuser or user.has_perm(PRIVILEGED_PERMISSION)
