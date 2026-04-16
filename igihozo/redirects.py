from django.contrib.auth import REDIRECT_FIELD_NAME
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme


def get_safe_redirect(request, fallback_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    candidate = request.POST.get(redirect_field_name) or request.GET.get(redirect_field_name)
    if candidate and url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return fallback_url


def get_safe_redirect_for_template(request, redirect_field_name=REDIRECT_FIELD_NAME):
    return get_safe_redirect(request, fallback_url="", redirect_field_name=redirect_field_name)


DEFAULT_POST_AUTH_REDIRECT = reverse_lazy("igihozo:account")
