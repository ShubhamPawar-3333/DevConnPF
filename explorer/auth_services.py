"""
GitHub OAuth service for managing authentication flow.

Handles OAuth initiation, callback processing, and token revocation.
"""

import logging

import requests
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from social_django.utils import load_strategy, load_backend

from explorer.encryption import TokenEncryptionService

logger = logging.getLogger(__name__)


class GitHubOAuthService:
    """Manages the GitHub OAuth flow: initiation, callback, and token revocation."""

    GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_REVOKE_URL = "https://api.github.com/applications/{client_id}/token"

    def __init__(self):
        self.client_id = settings.SOCIAL_AUTH_GITHUB_KEY
        self.client_secret = settings.SOCIAL_AUTH_GITHUB_SECRET
        self.scopes = settings.SOCIAL_AUTH_GITHUB_SCOPE
        self.encryption_service = TokenEncryptionService()

    def initiate_oauth(self, request):
        """Redirect the user to GitHub's OAuth authorization page.

        Uses social-auth-app-django's built-in begin flow to construct
        the proper redirect URL with state parameter for CSRF protection.

        Args:
            request: The Django HTTP request.

        Returns:
            HttpResponseRedirect to GitHub OAuth authorization URL.
        """
        strategy = load_strategy(request)
        backend = load_backend(strategy, "github", redirect_uri=None)
        return redirect(backend.auth_url())

    def handle_callback(self, request):
        """Process the OAuth callback from GitHub.

        This is handled by social-auth-app-django's complete flow.
        After successful authentication, the pipeline stores the encrypted token.

        Args:
            request: The Django HTTP request containing the OAuth code.

        Returns:
            The authenticated User instance.

        Raises:
            AuthException: If the OAuth flow fails.
        """
        # social-auth-app-django handles the callback via its own URL patterns
        # This method is provided for explicit programmatic use if needed
        strategy = load_strategy(request)
        backend = load_backend(strategy, "github", redirect_uri=None)
        return backend.complete(request=request)

    def revoke_token(self, user):
        """Revoke the user's GitHub access token and clear stored data.

        Attempts to revoke the token via GitHub's API, then clears the
        encrypted token from the user model regardless of revocation success.

        Args:
            user: The User instance whose token should be revoked.
        """
        if user.github_token_encrypted:
            try:
                token = self.encryption_service.decrypt(bytes(user.github_token_encrypted))
                # Attempt to revoke the token on GitHub's side
                self._revoke_on_github(token)
            except Exception as e:
                logger.warning(
                    "Failed to revoke GitHub token for user %s: %s",
                    user.username,
                    str(e),
                )
            finally:
                # Always clear the stored token regardless of revocation success
                user.github_token_encrypted = None
                user.save(update_fields=["github_token_encrypted"])

    def _revoke_on_github(self, token: str):
        """Attempt to revoke the token via GitHub's OAuth application API.

        Args:
            token: The plaintext access token to revoke.
        """
        if not self.client_id or not self.client_secret:
            logger.warning("Cannot revoke token: GitHub OAuth credentials not configured.")
            return

        url = self.GITHUB_REVOKE_URL.format(client_id=self.client_id)
        try:
            response = requests.delete(
                url,
                auth=(self.client_id, self.client_secret),
                json={"access_token": token},
                headers={"Accept": "application/vnd.github+json"},
                timeout=10,
            )
            if response.status_code == 204:
                logger.info("Successfully revoked GitHub token.")
            else:
                logger.warning(
                    "GitHub token revocation returned status %d", response.status_code
                )
        except requests.RequestException as e:
            logger.warning("Network error during token revocation: %s", str(e))
