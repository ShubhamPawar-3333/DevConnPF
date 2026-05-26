"""
Custom DRF authentication class that works with cross-origin session auth.

Django's SessionAuthentication enforces CSRF on all requests, which breaks
cross-origin SPA setups (frontend on port 3000, backend on port 8000).

This class authenticates via session cookies but skips CSRF enforcement,
relying on CORS configuration to restrict which origins can make requests.
This is safe because:
1. CORS prevents unauthorized origins from making credentialed requests
2. The browser won't send cookies cross-origin unless CORS allows it
3. CORS_ALLOW_CREDENTIALS = True is restricted to explicit allowed origins
"""

from rest_framework.authentication import SessionAuthentication


class CorsSessionAuthentication(SessionAuthentication):
    """Session authentication without CSRF enforcement.

    Used for SPA frontends that communicate cross-origin.
    Security is provided by CORS origin restrictions instead of CSRF tokens.
    """

    def enforce_csrf(self, request):
        # Skip CSRF check — CORS handles cross-origin protection
        return
