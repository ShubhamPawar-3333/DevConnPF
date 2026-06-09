"""
Task 13.4 — Unit tests for GitHubImportService with mocked GitHub API.
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from profiles.models import Profile
from profiles.services import (
    GitHubImportError,
    GitHubImportService,
    GitHubTokenMissingError,
)

User = get_user_model()


def make_user(username):
    return User.objects.create_user(username=username, email=f"{username}@x.com", password="pass")


def make_profile(user, slug):
    return Profile.objects.create(user=user, slug=slug, display_name="Dev")


class TestGitHubImportPreview(TestCase):
    """GitHub import preview endpoint behavior."""

    def setUp(self):
        self.user = make_user("gi-user")
        self.profile = make_profile(self.user, "gi-dev")
        self.service = GitHubImportService()

    def test_user_without_token_raises_missing_error(self):
        self.user.github_token_encrypted = None
        with self.assertRaises(GitHubTokenMissingError) as ctx:
            self.service.fetch_github_profile(self.user)
        self.assertIn("No GitHub token", str(ctx.exception))

    @patch("profiles.services.requests.get")
    def test_preview_returns_github_and_current_values(self, mock_get):
        """Verify fetch returns correct field mapping."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "avatar_url": "https://avatars.github.com/u/123",
            "name": "Jane Dev",
            "bio": "Python developer",
        }
        mock_get.return_value = mock_response
        self.user.github_token_encrypted = b"encrypted-token"
        with patch("profiles.services.TokenEncryptionService") as mock_enc:
            mock_enc.return_value.decrypt.return_value = "gh-real-token"
            result = self.service.fetch_github_profile(self.user)
        self.assertEqual(result["avatar_url"], "https://avatars.github.com/u/123")
        self.assertEqual(result["display_name"], "Jane Dev")
        self.assertEqual(result["bio"], "Python developer")

    @patch("profiles.services.requests.get")
    def test_null_github_fields_omitted_from_result(self, mock_get):
        """Fields returned as null by GitHub should not appear in result."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "avatar_url": "https://avatars.github.com/u/123",
            "name": None,
            "bio": "",
        }
        mock_get.return_value = mock_response
        self.user.github_token_encrypted = b"encrypted-token"
        with patch("profiles.services.TokenEncryptionService") as mock_enc:
            mock_enc.return_value.decrypt.return_value = "gh-real-token"
            result = self.service.fetch_github_profile(self.user)
        self.assertIn("avatar_url", result)
        self.assertNotIn("display_name", result)
        self.assertNotIn("bio", result)

    @patch("profiles.services.requests.get")
    def test_github_401_response_raises_with_reauth_message(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        self.user.github_token_encrypted = b"encrypted-token"
        with patch("profiles.services.TokenEncryptionService") as mock_enc:
            mock_enc.return_value.decrypt.return_value = "bad-token"
            with self.assertRaises(GitHubImportError) as ctx:
                self.service.fetch_github_profile(self.user)
        self.assertIn("expired or revoked", str(ctx.exception))

    @patch("profiles.services.requests.get")
    def test_encrypted_token_decrypted_and_used_in_header(self, mock_get):
        """Confirm the decrypted token is passed as Bearer header."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {"avatar_url": "https://x.com/a.png", "name": "Dev", "bio": None}
        mock_get.return_value = mock_response
        self.user.github_token_encrypted = b"encrypted-token"
        with patch("profiles.services.TokenEncryptionService") as mock_enc:
            mock_enc.return_value.decrypt.return_value = "decrypted-token-123"
            self.service.fetch_github_profile(self.user)
        call_kwargs = mock_get.call_args[1]
        self.assertIn("headers", call_kwargs)
        self.assertIn("Bearer decrypted-token-123", call_kwargs["headers"]["Authorization"])

    @patch("profiles.services.requests.get")
    def test_github_api_timeout_raises_import_error(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = req_lib.Timeout("timed out")
        self.user.github_token_encrypted = b"encrypted-token"
        with patch("profiles.services.TokenEncryptionService") as mock_enc:
            mock_enc.return_value.decrypt.return_value = "token"
            with self.assertRaises(GitHubImportError):
                self.service.fetch_github_profile(self.user)
