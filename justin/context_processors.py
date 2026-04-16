from .models import Profile


def role_context(request):
    """Add role information to all template contexts."""
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            return {
                'user_role': profile.role,
                'is_privileged': profile.is_privileged,
                'is_admin': profile.is_admin,
            }
        except Profile.DoesNotExist:
            pass
    return {
        'user_role': None,
        'is_privileged': False,
        'is_admin': False,
    }