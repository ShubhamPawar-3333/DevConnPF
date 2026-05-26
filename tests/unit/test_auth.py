"""
Unit tests for the authentication module: encryption service, auth views, and pipeline.
"""

import pytest
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet

from django.test import RequestFactory

# Generate a valid Fernet key for testing
TEST_FERNET_KEY = Fernet.generate_key().decode()


@pytest.fixture
def fernet_settings(settings):
    """Configure a valid Fernet key for tests."""
    settings.FERNET_KEY = TEST_FERNET_KEY
    return settings


@pytest.fixture
def request_factory():
    return RequestFactory()


def _add_middleware(request):
    """Add a mock session and message support to a request."""
    from django.contrib.messages.storage.fallback import FallbackStorage

    # Use a simple dict as session to avoid DB/cache dependencies
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


class TestTokenEncryptionService:
    """Tests for TokenEncryptionService."""

    def test_encrypt_returns_bytes(self, fernet_settings):
        from explorer.encryption import TokenEncryptionService

        service = TokenEncryptionService()
        result = service.encrypt("ghp_test_token_123")
        assert isinstance(result, bytes)

    def test_decrypt_returns_original_token(self, fernet_settings):
        from explorer.encryption import TokenEncryptionService

        service = TokenEncryptionService()
        original = "ghp_abcdef1234567890"
        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_decrypt_roundtrip(self, fernet_settings):
        from explorer.encryption import TokenEncryptionService

        service = TokenEncryptionService()
        token = "gho_16C7e42F292c6912E7710c838347Ae178B4a"
        assert service.decrypt(service.encrypt(token)) == token

    def test_encrypt_empty_token_raises(self, fernet_settings):
        from explorer.encryption import TokenEncryptionService

        service = TokenEncryptionService()
        with pytest.raises(ValueError, match="cannot be empty"):
            service.encrypt("")

    def test_encrypt_none_token_raises(self, fernet_settings):
        from explorer.encryption import TokenEncryptionService

        service = TokenEncryptionService()
        with pytest.raises(ValueError, match="cannot be empty"):
            service.encrypt(None)

    def test_decrypt_empty_raises(self, fernet_settings):
        from explorer.encryption import TokenEncryptionService

        service = TokenEncryptionService()
        with pytest.raises(ValueError, match="cannot be empty"):
            service.decrypt(b"")

    def test_decrypt_none_raises(self, fernet_settings):
        from explorer.encryption import TokenEncryptionService

        service = TokenEncryptionService()
        with pytest.raises(ValueError, match="cannot be empty"):
            service.decrypt(None)

    def test_missing_fernet_key_raises(self, settings):
        from explorer.encryption import TokenEncryptionService

        settings.FERNET_KEY = ""
        with pytest.raises(ValueError, match="FERNET_KEY is not configured"):
            TokenEncryptionService()

    def test_different_tokens_produce_different_ciphertext(self, fernet_settings):
        from explorer.encryption import TokenEncryptionService

        service = TokenEncryptionService()
        enc1 = service.encrypt("token_one")
        enc2 = service.encrypt("token_two")
        assert enc1 != enc2

    def test_same_token_produces_different_ciphertext_each_time(self, fernet_settings):
        """Fernet includes a timestamp and random IV, so same input != same output."""
        from explorer.encryption import TokenEncryptionService

        service = TokenEncryptionService()
        token = "ghp_same_token"
        enc1 = service.encrypt(token)
        enc2 = service.encrypt(token)
        # Ciphertexts differ but both decrypt to the same value
        assert enc1 != enc2
        assert service.decrypt(enc1) == service.decrypt(enc2) == token


class TestPipeline:
    """Tests for the custom social auth pipeline step."""

    def test_store_encrypted_token_saves_to_user(self, fernet_settings):
        from explorer.pipeline import store_encrypted_token
        from explorer.encryption import TokenEncryptionService

        user = MagicMock()
        user.username = "testuser"
        user.github_token_encrypted = None
        backend = MagicMock()
        backend.name = "github"
        response = {"access_token": "ghp_pipeline_test_token"}

        store_encrypted_token(backend, user, response)

        # Verify the token was encrypted and saved
        user.save.assert_called_once_with(update_fields=["github_token_encrypted"])
        assert user.github_token_encrypted is not None

        # Verify the stored token decrypts correctly
        service = TokenEncryptionService()
        decrypted = service.decrypt(user.github_token_encrypted)
        assert decrypted == "ghp_pipeline_test_token"

    def test_store_encrypted_token_skips_non_github_backend(self, fernet_settings):
        from explorer.pipeline import store_encrypted_token

        user = MagicMock()
        user.username = "testuser2"
        user.github_token_encrypted = None
        backend = MagicMock()
        backend.name = "google"
        response = {"access_token": "some_token"}

        store_encrypted_token(backend, user, response)

        user.save.assert_not_called()

    def test_store_encrypted_token_handles_missing_token(self, fernet_settings):
        from explorer.pipeline import store_encrypted_token

        user = MagicMock()
        user.username = "testuser3"
        user.github_token_encrypted = None
        backend = MagicMock()
        backend.name = "github"
        response = {}  # No access_token

        store_encrypted_token(backend, user, response)

        user.save.assert_not_called()


class TestAuthViews:
    """Tests for authentication views."""

    def test_login_view_redirects_to_github(self, request_factory):
        from explorer.views import login_view

        request = request_factory.get("/api/auth/login/")
        request.user = MagicMock(is_authenticated=False)
        request = _add_middleware(request)

        response = login_view(request)
        assert response.status_code == 302
        assert "github" in response.url

    def test_login_view_redirects_authenticated_user_to_dashboard(
        self, request_factory, settings
    ):
        from explorer.views import login_view

        settings.LOGIN_REDIRECT_URL = "http://localhost:3000/dashboard"
        request = request_factory.get("/api/auth/login/")
        request.user = MagicMock(is_authenticated=True)
        request = _add_middleware(request)

        response = login_view(request)
        assert response.status_code == 302
        assert response.url == "http://localhost:3000/dashboard"

    def test_github_auth_url_returns_social_auth_entrypoint(
        self, request_factory, settings
    ):
        from explorer.views import github_auth_url_view

        settings.SOCIAL_AUTH_GITHUB_KEY = "test-client-id"

        request = request_factory.get("/api/auth/github/url/")
        request.user = MagicMock(is_authenticated=False)
        request = _add_middleware(request)

        response = github_auth_url_view(request)

        assert response.status_code == 200
        assert response.data["url"] == "/api/auth/github/"

    def test_current_user_view_returns_anonymous_session(self, request_factory):
        from explorer.views import current_user_view

        request = request_factory.get("/api/auth/me/")
        request.user = MagicMock(is_authenticated=False)

        response = current_user_view(request)

        assert response.status_code == 200
        assert response.data == {
            "isAuthenticated": False,
            "user": None,
        }

    def test_current_user_view_returns_authenticated_session(self, request_factory):
        from explorer.views import current_user_view

        user = MagicMock()
        user.is_authenticated = True
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.language_preference = "en"
        user.social_auth.filter.return_value.first.return_value = MagicMock(
            extra_data={"avatar_url": "https://example.com/avatar.png"}
        )

        request = request_factory.get("/api/auth/me/")
        request.user = user

        response = current_user_view(request)

        assert response.status_code == 200
        assert response.data == {
            "isAuthenticated": True,
            "user": {
                "id": 1,
                "username": "testuser",
                "email": "test@example.com",
                "languagePreference": "en",
                "avatarUrl": "https://example.com/avatar.png",
            },
        }

    @patch("requests.get")
    @patch("requests.post")
    def test_github_callback_exchange_sends_same_redirect_uri(
        self, mock_post, mock_get, request_factory, settings
    ):
        from explorer.views import github_callback_api_view

        settings.SOCIAL_AUTH_GITHUB_KEY = "test-client-id"
        settings.SOCIAL_AUTH_GITHUB_SECRET = "test-client-secret"
        settings.FRONTEND_URL = "http://localhost:3000/"

        mock_post.return_value.json.return_value = {
            "error": "bad_verification_code",
            "error_description": "The code passed is incorrect or expired.",
        }

        request = request_factory.post(
            "/api/auth/github/callback/",
            {"code": "test-code", "state": "state-token"},
            content_type="application/json",
        )
        request.user = MagicMock(is_authenticated=False)
        request = _add_middleware(request)
        request.session["oauth_state"] = "state-token"

        response = github_callback_api_view(request)

        assert response.status_code == 400
        mock_get.assert_not_called()
        mock_post.assert_called_once()
        assert mock_post.call_args.kwargs["json"]["redirect_uri"] == (
            "http://localhost:3000/auth/callback"
        )

    def test_oauth_error_view_access_denied(self, request_factory):
        from explorer.views import oauth_callback_view

        request = request_factory.get(
            "/api/auth/error/",
            {"error": "access_denied", "error_description": "The user denied access"},
        )
        request.user = MagicMock(is_authenticated=False)
        request = _add_middleware(request)

        response = oauth_callback_view(request)
        assert response.status_code == 302

    def test_oauth_error_view_generic_error(self, request_factory):
        from explorer.views import oauth_callback_view

        request = request_factory.get(
            "/api/auth/error/",
            {"error": "server_error", "error_description": "Something went wrong"},
        )
        request.user = MagicMock(is_authenticated=False)
        request = _add_middleware(request)

        response = oauth_callback_view(request)
        assert response.status_code == 302

    def test_oauth_error_view_no_error_param(self, request_factory):
        from explorer.views import oauth_callback_view

        request = request_factory.get("/api/auth/error/")
        request.user = MagicMock(is_authenticated=False)
        request = _add_middleware(request)

        response = oauth_callback_view(request)
        assert response.status_code == 302

    @patch("explorer.views.GitHubOAuthService")
    @patch("explorer.views.logout")
    def test_logout_view_revokes_token_and_logs_out(
        self, mock_logout, mock_service_cls, request_factory, fernet_settings
    ):
        from explorer.views import logout_view

        user = MagicMock()
        user.is_authenticated = True
        request = request_factory.post("/api/auth/logout/")
        request.user = user
        request = _add_middleware(request)

        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service

        response = logout_view(request)
        assert response.status_code == 302
        assert response.url == "/"
        mock_service.revoke_token.assert_called_once_with(user)
        mock_logout.assert_called_once_with(request)

    @patch("explorer.views.GitHubOAuthService")
    def test_logout_view_unauthenticated_user_redirects(
        self, mock_service_cls, request_factory
    ):
        from explorer.views import logout_view

        request = request_factory.post("/api/auth/logout/")
        request.user = MagicMock(is_authenticated=False)
        request = _add_middleware(request)

        response = logout_view(request)
        assert response.status_code == 302
        assert response.url == "/"
        mock_service_cls.assert_not_called()
