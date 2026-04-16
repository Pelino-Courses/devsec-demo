from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied

STUDENT_GROUP = 'student'
INSTRUCTOR_GROUP = 'instructor'


def ensure_role_groups():
    for group_name in (STUDENT_GROUP, INSTRUCTOR_GROUP):
        Group.objects.get_or_create(name=group_name)


def is_instructor(user):
    return user.is_authenticated and (
        user.is_staff
        or user.is_superuser
        or user.groups.filter(name=INSTRUCTOR_GROUP).exists()
    )


def instructor_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if is_instructor(request.user):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied()

    return _wrapped
