"""
Business logic services for the profiles app.

This file contains three service classes:
- ProfileService: slug validation and availability checks
- GitHubImportService: fetching and applying GitHub profile data
- FollowService: follow/unfollow and count synchronisation
"""

import re

import requests
from django.core.exceptions import ValidationError

from explorer.encryption import TokenEncryptionService
from profiles.models import Follow, Profile


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class GitHubTokenMissingError(Exception):
    """Raised when the user has no stored GitHub token."""
    pass


class GitHubImportError(Exception):
    """Raised when the GitHub API call fails."""
    pass


# ---------------------------------------------------------------------------
# ProfileService
# ---------------------------------------------------------------------------

class ProfileService:
    """Handles slug validation and availability checks."""

    RESERVED_SLUGS = frozenset([
        "admin", "api", "auth", "settings", "dashboard",
        "login", "explore", "shared", "repos", "search",
    ])

    SLUG_PATTERN = re.compile(r'^[a-z][a-z0-9\-]{2,39}$')

    def validate_slug(self, slug: str, exclude_profile_id: int | None = None) -> None:
        """Validate slug format, reserved words, and uniqueness.

        Args:
            slug: The candidate slug string.
            exclude_profile_id: Profile ID to exclude from uniqueness check
                (used when updating an existing profile's own slug).

        Raises:
            ValidationError: If any validation rule is violated.
        """
        # Length check (3-40 characters)
        if not (3 <= len(slug) <= 40):
            raise ValidationError("Slug must be between 3 and 40 characters.")

        # Format check
        if not self.SLUG_PATTERN.match(slug):
            raise ValidationError(
                "Slug must start with a lowercase letter and contain only "
                "lowercase letters, numbers, and hyphens."
            )

        # Reserved words check
        if slug in self.RESERVED_SLUGS:
            raise ValidationError(f"The slug '{slug}' is reserved and cannot be used.")

        # Uniqueness check
        qs = Profile.objects.filter(slug=slug)
        if exclude_profile_id is not None:
            qs = qs.exclude(pk=exclude_profile_id)
        if qs.exists():
            raise ValidationError(f"The slug '{slug}' is already taken.")

    def is_slug_available(self, slug: str, exclude_profile_id: int | None = None) -> bool:
        """Return True if the slug passes all validation rules, False otherwise.

        Args:
            slug: The candidate slug string.
            exclude_profile_id: Profile ID to exclude from the uniqueness check.

        Returns:
            True if the slug is valid and available, False otherwise.
        """
        try:
            self.validate_slug(slug, exclude_profile_id=exclude_profile_id)
            return True
        except ValidationError:
            return False


# ---------------------------------------------------------------------------
# GitHubImportService
# ---------------------------------------------------------------------------

class GitHubImportService:
    """Fetches GitHub profile data using the user's stored OAuth token."""

    GITHUB_USER_URL = "https://api.github.com/user"
    TIMEOUT_SECONDS = 10

    def fetch_github_profile(self, user) -> dict:
        """Fetch avatar_url, name, and bio from the GitHub API.

        Decrypts the stored GitHub token from the user object, calls the
        GitHub /user endpoint, and returns only the fields that have actual
        (non-null, non-empty) values.

        Args:
            user: The authenticated User instance (explorer.User).

        Returns:
            A dict containing any non-null/non-empty values from:
            ``avatar_url``, ``display_name`` (mapped from GitHub's ``name``),
            and ``bio``.

        Raises:
            GitHubTokenMissingError: If no GitHub token is stored for the user.
            GitHubImportError: If the GitHub API request fails, times out, or
                returns a 401/403 response.
        """
        # Retrieve and decrypt the stored token
        if not user.github_token_encrypted:
            raise GitHubTokenMissingError("No GitHub token stored for this user.")

        encryption_service = TokenEncryptionService()
        token = encryption_service.decrypt(bytes(user.github_token_encrypted))

        # Call the GitHub API
        try:
            response = requests.get(
                self.GITHUB_USER_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                timeout=self.TIMEOUT_SECONDS,
            )
        except requests.Timeout as e:
            raise GitHubImportError(f"GitHub API request failed: {str(e)}")
        except requests.RequestException as e:
            raise GitHubImportError(f"GitHub API request failed: {str(e)}")

        # Handle auth errors
        if response.status_code in (401, 403):
            raise GitHubImportError(
                "GitHub token is expired or revoked. Please re-authenticate."
            )

        # Handle any other non-2xx response
        if not response.ok:
            raise GitHubImportError(
                f"GitHub API request failed: {response.status_code} {response.reason}"
            )

        # Build result dict — include only fields with actual values
        data = response.json()
        result: dict = {}

        if data.get("avatar_url"):
            result["avatar_url"] = data["avatar_url"]

        if data.get("name"):
            result["display_name"] = data["name"]

        if data.get("bio"):
            result["bio"] = data["bio"]

        return result


# ---------------------------------------------------------------------------
# FollowService
# ---------------------------------------------------------------------------

class FollowService:
    def follow(self, follower: "Follow", target: "Follow") -> "Follow":
        """Create a follow relationship between two profiles.

        Raises ValidationError if follower and target are the same profile.
        Uses get_or_create for idempotence — returns existing relationship
        without duplicating it.
        """
        if follower.pk == target.pk:
            raise ValidationError("You cannot follow yourself.")

        follow_obj, created = Follow.objects.get_or_create(
            follower=follower,
            target=target,
        )

        if created:
            self.sync_counts(follower)
            self.sync_counts(target)

        return follow_obj

    def unfollow(self, follower: "Follow", target: "Follow") -> None:
        """Remove a follow relationship between two profiles.

        Raises Follow.DoesNotExist if the relationship doesn't exist.
        Syncs follower/following counts after deletion.
        """
        try:
            Follow.objects.get(follower=follower, target=target).delete()
        except Follow.DoesNotExist:
            raise Follow.DoesNotExist("No follow relationship exists.")

        self.sync_counts(follower)
        self.sync_counts(target)

    def sync_counts(self, profile: "Follow") -> None:
        """Recalculate and persist follower_count and following_count for a profile.

        Counts are derived from actual Follow records rather than incremented
        in-memory, keeping them consistent after any sequence of operations.
        """
        profile.follower_count = Follow.objects.filter(target=profile).count()
        profile.following_count = Follow.objects.filter(follower=profile).count()
        profile.save(update_fields=["follower_count", "following_count"])
