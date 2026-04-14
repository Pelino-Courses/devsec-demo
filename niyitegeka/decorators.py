from django.contrib.auth.decorators import user_passes_test


def staff_required(view_func):
    decorated = user_passes_test(
        lambda u: u.is_active and u.is_staff,
        login_url='/auth/login/'
    )(view_func)
    return decorated
