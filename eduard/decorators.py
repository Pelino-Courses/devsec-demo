from django.core.exceptions import PermissionDenied


def instructor_required(view_func):
    """
    Decorator that restricts a view to users in the 'Instructor' group
    or staff/superusers. Raises PermissionDenied (HTTP 403) for
    authenticated users who lack the role, so they know they are logged
    in but not authorised — distinct from a login redirect.
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.conf import settings
            from django.shortcuts import redirect
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        if (
            request.user.is_staff
            or request.user.is_superuser
            or request.user.groups.filter(name='Instructor').exists()
        ):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    wrapper.__name__ = view_func.__name__
    return wrapper