from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings

def get_safe_redirect_url(request, default_url):
    """
    Safely extract and validate a redirect URL from the request.
    Checks 'next' in POST and then GET parameters.
    """
    redirect_to = request.POST.get('next', request.GET.get('next'))
    
    # Check if URL is safe: internal and uses allowed schemes
    if redirect_to and url_has_allowed_host_and_scheme(
        url=redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect_to
        
    return default_url
