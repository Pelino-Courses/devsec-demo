from functools import wraps

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def instructor_required(view_func):
    """
    Restrict a view to the Instructor role.

    - Anonymous users are redirected to the login page (preserving the next URL).
    - Authenticated users without the 'can_view_all_profiles' permission receive
      a 403 Forbidden response rather than a login redirect, so they are not
      misled into thinking they simply need to sign in again.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        if not request.user.has_perm("uwamahoro_joseline.can_view_all_profiles"):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped
