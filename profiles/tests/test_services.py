"""
Task 13.2 — Unit tests for ProfileService, GitHubImportService, and FollowService.
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from profiles.models import Follow, Profile
from profiles.services import (
    FollowService,
    GitHubImportError,
    GitHubImportService,
    GitHubTokenMissingError,
    ProfileService,
)

User = get_user_model()


def make_user(username):
    return User.objects.create_user(username=username, email=f"{username}@x.com", password="pass")


def make_profile(user, slug):
    return Profile.objects.create(user=user, slug=slug, display_name="Dev")


# ---------------------------------------------------------------------------
# ProfileService
# ---------------------------------------------------------------------------

class TestProfileService(TestCase):

    def setUp(self):
        self.service = ProfileService()

    def test_reserved_slug_rejected(self):
        for slug in ["admin", "api", "auth", "settings", "dashboard", "login",
                     "explore", "shared", "repos", "search"]:
            with self.assertRaises(ValidationError):
                self.service.validate_slug(slug)

    def test_valid_slug_accepted(self):
        self.service.validate_slug("jane-dev")  # should not raise

    def test_slug_too_short_rejected(self):
        with self.assertRaises(ValidationError):
            self.service.validate_slug("ab")

    def test_slug_too_long_rejected(self):
        with self.assertRaises(ValidationError):
            self.service.validate_slug("a" * 41)

    def test_slug_starting_with_digit_rejected(self):
        with self.assertRaises(ValidationError):
            self.service.validate_slug("1badslug")

    def test_slug_with_uppercase_rejected(self):
        with self.assertRaises(ValidationError):
            self.service.validate_slug("BadSlug")

    def test_uniqueness_check_with_exclude(self):
        user = make_user("ps-u1")
        profile = make_profile(user, "existing-slug")
        # Should not raise when excluding own profile
        self.service.validate_slug("existing-slug", exclude_profile_id=profile.pk)
        # Should raise without exclude
        with self.assertRaises(ValidationError):
            self.service.validate_slug("existing-slug")

    def test_is_slug_available_returns_true_for_valid(self):
        self.assertTrue(self.service.is_slug_available("new-slug"))

    def test_is_slug_available_returns_false_for_reserved(self):
        self.assertFalse(self.service.is_slug_available("admin"))


# ---------------------------------------------------------------------------
# GitHubImportService
# ---------------------------------------------------------------------------

class TestGitHubImportService(TestCase):

    def setUp(self):
        self.service = GitHubImportService()

    def test_missing_token_raises_error(self):
        user = MagicMock()
        user.github_token_encrypted = None
        with self.assertRaises(GitHubTokenMissingError):
            self.service.fetch_github_profile(user)

    @patch("profiles.services.requests.get")
    def test_timeout_raises_github_import_error(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = req_lib.Timeout()
        user = MagicMock()
        user.github_token_encrypted = b"token"
        with patch("profiles.services.TokenEncryptionService") as mock_enc:
            mock_enc.return_value.decrypt.return_value = "gh-token"
            with self.assertRaises(GitHubImportError):
                self.service.fetch_github_profile(user)

    @patch("profiles.services.requests.get")
    def test_401_raises_github_import_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        user = MagicMock()
        user.github_token_encrypted = b"token"
        with patch("profiles.services.TokenEncryptionService") as mock_enc:
            mock_enc.return_value.decrypt.return_value = "gh-token"
            with self.assertRaises(GitHubImportError):
                self.service.fetch_github_profile(user)

    @patch("profiles.services.requests.get")
    def test_successful_fetch_returns_non_null_fields_only(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "avatar_url": "https://example.com/avatar.png",
            "name": "Jane Dev",
            "bio": None,
        }
        mock_get.return_value = mock_response
        user = MagicMock()
        user.github_token_encrypted = b"token"
        with patch("profiles.services.TokenEncryptionService") as mock_enc:
            mock_enc.return_value.decrypt.return_value = "gh-token"
            result = self.service.fetch_github_profile(user)
        self.assertIn("avatar_url", result)
        self.assertIn("display_name", result)
        self.assertNotIn("bio", result)  # null bio omitted


# ---------------------------------------------------------------------------
# FollowService
# ---------------------------------------------------------------------------

class TestFollowService(TestCase):

    def setUp(self):
        self.service = FollowService()
        self.u1 = make_user("fs-u1")
        self.u2 = make_user("fs-u2")
        self.p1 = make_profile(self.u1, "fs-p1")
        self.p2 = make_profile(self.u2, "fs-p2")

    def test_follow_creates_record(self):
        follow = self.service.follow(self.p1, self.p2)
        self.assertIsNotNone(follow.pk)

    def test_follow_idempotent_via_get_or_create(self):
        self.service.follow(self.p1, self.p2)
        self.service.follow(self.p1, self.p2)
        self.assertEqual(Follow.objects.filter(follower=self.p1, target=self.p2).count(), 1)

    def test_self_follow_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.service.follow(self.p1, self.p1)

    def test_unfollow_removes_record(self):
        self.service.follow(self.p1, self.p2)
        self.service.unfollow(self.p1, self.p2)
        self.assertFalse(Follow.objects.filter(follower=self.p1, target=self.p2).exists())

    def test_unfollow_not_following_raises(self):
        with self.assertRaises(Follow.DoesNotExist):
            self.service.unfollow(self.p1, self.p2)

    def test_sync_counts_correct(self):
        self.service.follow(self.p1, self.p2)
        self.service.sync_counts(self.p2)
        self.p2.refresh_from_db()
        self.assertEqual(self.p2.follower_count, 1)
        self.assertEqual(self.p2.following_count, 0)
