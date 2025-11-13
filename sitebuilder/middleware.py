from urllib.parse import urlparse
from django.http import HttpResponseRedirect
import config


class CanonicalHostMiddleware:
    """
    Forces all requests to use the canonical host defined in config.SITE_URL.
    This unifies session cookies across tabs and prevents accidental login loss
    when switching between 127.0.0.1 and localhost.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        parsed = urlparse(getattr(config, "SITE_URL", "http://localhost:8000"))
        self.scheme = parsed.scheme or "http"
        self.netloc = parsed.netloc or "localhost:8000"

    def __call__(self, request):
        host = request.get_host()
        # Redirect if the requested host doesn't match the canonical netloc
        if host and host.lower() != self.netloc.lower():
            return HttpResponseRedirect(f"{self.scheme}://{self.netloc}{request.get_full_path()}")
        return self.get_response(request)
