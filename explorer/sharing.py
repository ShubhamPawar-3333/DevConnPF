"""
Sharing service for public repository views.

Handles token generation, shared view lifecycle, and public access control.
"""

import secrets

from explorer.models import Repository, SharedView


class SharingService:
    """Manages public sharing of explored repositories."""

    def enable_sharing(self, repository: Repository) -> SharedView:
        """Enable sharing for a repository.

        Generates a cryptographically random URL-safe token (≥ 22 chars),
        creates a SharedView record, and returns it.

        If sharing is already enabled, returns the existing SharedView.
        """
        # Check if a SharedView already exists for this repository
        try:
            shared_view = SharedView.objects.get(repository=repository)
            if shared_view.is_active:
                return shared_view
            # Reactivate with a new token
            shared_view.token = self._generate_token()
            shared_view.is_active = True
            shared_view.save()
            return shared_view
        except SharedView.DoesNotExist:
            pass

        shared_view = SharedView.objects.create(
            repository=repository,
            token=self._generate_token(),
            is_active=True,
        )
        return shared_view

    def disable_sharing(self, repository: Repository) -> None:
        """Disable sharing for a repository.

        Sets is_active=False on the SharedView, ensuring 404 within 5 seconds.
        """
        try:
            shared_view = SharedView.objects.get(repository=repository)
            shared_view.is_active = False
            shared_view.save()
        except SharedView.DoesNotExist:
            pass

    def regenerate_url(self, repository: Repository) -> SharedView:
        """Regenerate the share URL for a repository.

        Creates a new token and invalidates the old one immediately.
        If no SharedView exists, creates one.
        """
        try:
            shared_view = SharedView.objects.get(repository=repository)
            shared_view.token = self._generate_token()
            shared_view.is_active = True
            shared_view.save()
            return shared_view
        except SharedView.DoesNotExist:
            return self.enable_sharing(repository)

    def get_shared_repository(self, token: str) -> Repository | None:
        """Retrieve the repository for a given share token.

        Returns None for invalid tokens, inactive shares, or deleted repositories.
        """
        try:
            shared_view = SharedView.objects.select_related(
                "repository", "repository__user"
            ).get(token=token, is_active=True)
            return shared_view.repository
        except SharedView.DoesNotExist:
            return None

    def _generate_token(self) -> str:
        """Generate a cryptographically random URL-safe token (≥ 22 chars).

        Uses secrets.token_urlsafe(24) which produces 32 URL-safe characters.
        """
        return secrets.token_urlsafe(24)
