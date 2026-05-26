"""
Unit tests for the sharing service and shared view endpoints.
"""

import pytest
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate

from explorer.models import Repository, SharedView, User
from explorer.sharing import SharingService


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def repository(db, user):
    """Create a test repository."""
    return Repository.objects.create(
        user=user,
        name="test-repo",
        source_type="github",
        github_full_name="testuser/test-repo",
        status="ready",
    )


@pytest.fixture
def sharing_service():
    """Create a SharingService instance."""
    return SharingService()


class TestSharingService:
    """Tests for the SharingService class."""

    def test_enable_sharing_creates_shared_view(self, sharing_service, repository):
        """Test that enable_sharing creates a SharedView record."""
        shared_view = sharing_service.enable_sharing(repository)

        assert shared_view is not None
        assert shared_view.repository == repository
        assert shared_view.is_active is True
        assert len(shared_view.token) >= 22

    def test_enable_sharing_returns_existing_active_view(self, sharing_service, repository):
        """Test that enable_sharing returns existing active SharedView."""
        first = sharing_service.enable_sharing(repository)
        second = sharing_service.enable_sharing(repository)

        assert first.id == second.id
        assert first.token == second.token

    def test_enable_sharing_reactivates_inactive_view(self, sharing_service, repository):
        """Test that enable_sharing reactivates an inactive SharedView with new token."""
        shared_view = sharing_service.enable_sharing(repository)
        old_token = shared_view.token

        sharing_service.disable_sharing(repository)
        reactivated = sharing_service.enable_sharing(repository)

        assert reactivated.is_active is True
        assert reactivated.token != old_token

    def test_disable_sharing_sets_inactive(self, sharing_service, repository):
        """Test that disable_sharing sets is_active=False."""
        sharing_service.enable_sharing(repository)
        sharing_service.disable_sharing(repository)

        shared_view = SharedView.objects.get(repository=repository)
        assert shared_view.is_active is False

    def test_disable_sharing_no_shared_view(self, sharing_service, repository):
        """Test that disable_sharing does nothing if no SharedView exists."""
        # Should not raise
        sharing_service.disable_sharing(repository)

    def test_regenerate_url_creates_new_token(self, sharing_service, repository):
        """Test that regenerate_url creates a new token."""
        original = sharing_service.enable_sharing(repository)
        old_token = original.token

        regenerated = sharing_service.regenerate_url(repository)

        assert regenerated.token != old_token
        assert regenerated.is_active is True
        assert len(regenerated.token) >= 22

    def test_regenerate_url_invalidates_old_token(self, sharing_service, repository):
        """Test that regenerate_url invalidates the old token immediately."""
        original = sharing_service.enable_sharing(repository)
        old_token = original.token

        sharing_service.regenerate_url(repository)

        # Old token should not resolve
        result = sharing_service.get_shared_repository(old_token)
        assert result is None

    def test_regenerate_url_creates_if_none_exists(self, sharing_service, repository):
        """Test that regenerate_url creates a SharedView if none exists."""
        shared_view = sharing_service.regenerate_url(repository)

        assert shared_view is not None
        assert shared_view.is_active is True
        assert len(shared_view.token) >= 22

    def test_get_shared_repository_valid_token(self, sharing_service, repository):
        """Test that get_shared_repository returns the repository for a valid token."""
        shared_view = sharing_service.enable_sharing(repository)

        result = sharing_service.get_shared_repository(shared_view.token)
        assert result == repository

    def test_get_shared_repository_invalid_token(self, sharing_service, db):
        """Test that get_shared_repository returns None for invalid token."""
        result = sharing_service.get_shared_repository("nonexistent-token")
        assert result is None

    def test_get_shared_repository_inactive_share(self, sharing_service, repository):
        """Test that get_shared_repository returns None for inactive share."""
        shared_view = sharing_service.enable_sharing(repository)
        sharing_service.disable_sharing(repository)

        result = sharing_service.get_shared_repository(shared_view.token)
        assert result is None

    def test_token_is_url_safe(self, sharing_service, repository):
        """Test that generated tokens contain only URL-safe characters."""
        import re

        shared_view = sharing_service.enable_sharing(repository)
        # URL-safe characters: alphanumeric, hyphen, underscore
        assert re.match(r'^[A-Za-z0-9_-]+$', shared_view.token)

    def test_token_minimum_length(self, sharing_service, repository):
        """Test that generated tokens are at least 22 characters."""
        shared_view = sharing_service.enable_sharing(repository)
        assert len(shared_view.token) >= 22


class TestSharingViews:
    """Tests for the sharing API endpoints."""

    @pytest.fixture
    def api_factory(self):
        return APIRequestFactory()

    def test_enable_sharing_endpoint(self, api_factory, user, repository):
        """Test POST /api/repositories/{id}/share/ enables sharing."""
        from explorer.views import repository_share_view

        request = api_factory.post(f"/api/repositories/{repository.id}/share/")
        force_authenticate(request, user=user)
        response = repository_share_view(request, repository_id=repository.id)

        assert response.status_code == 200
        assert "token" in response.data
        assert "share_url" in response.data
        assert response.data["is_active"] is True
        assert len(response.data["token"]) >= 22

    def test_disable_sharing_endpoint(self, api_factory, user, repository):
        """Test DELETE /api/repositories/{id}/share/ disables sharing."""
        from explorer.views import repository_share_view

        # First enable sharing
        SharingService().enable_sharing(repository)

        request = api_factory.delete(f"/api/repositories/{repository.id}/share/")
        force_authenticate(request, user=user)
        response = repository_share_view(request, repository_id=repository.id)

        assert response.status_code == 200
        assert response.data["message"] == "Sharing disabled."

    def test_regenerate_share_url_endpoint(self, api_factory, user, repository):
        """Test POST /api/repositories/{id}/share/regenerate/ regenerates URL."""
        from explorer.views import repository_share_regenerate_view

        # First enable sharing
        original = SharingService().enable_sharing(repository)
        old_token = original.token

        request = api_factory.post(
            f"/api/repositories/{repository.id}/share/regenerate/"
        )
        force_authenticate(request, user=user)
        response = repository_share_regenerate_view(
            request, repository_id=repository.id
        )

        assert response.status_code == 200
        assert response.data["token"] != old_token
        assert response.data["is_active"] is True

    def test_shared_repository_public_endpoint(self, api_factory, user, repository):
        """Test GET /api/shared/{token}/ returns repository data without auth."""
        from explorer.views import shared_repository_view

        shared_view = SharingService().enable_sharing(repository)

        request = api_factory.get(f"/api/shared/{shared_view.token}/")
        # No authentication
        response = shared_repository_view(request, token=shared_view.token)

        assert response.status_code == 200
        assert response.data["repository_name"] == "test-repo"
        assert response.data["owner_username"] == "testuser"
        assert response.data["read_only"] is True
        assert response.data["search_enabled"] is True
        assert "tree" in response.data

    def test_shared_repository_invalid_token_returns_404(self, api_factory, db):
        """Test GET /api/shared/{token}/ returns 404 for invalid token."""
        from explorer.views import shared_repository_view

        request = api_factory.get("/api/shared/invalid-token/")
        response = shared_repository_view(request, token="invalid-token")

        assert response.status_code == 404

    def test_shared_repository_inactive_share_returns_404(
        self, api_factory, user, repository
    ):
        """Test GET /api/shared/{token}/ returns 404 for inactive share."""
        from explorer.views import shared_repository_view

        service = SharingService()
        shared_view = service.enable_sharing(repository)
        token = shared_view.token
        service.disable_sharing(repository)

        request = api_factory.get(f"/api/shared/{token}/")
        response = shared_repository_view(request, token=token)

        assert response.status_code == 404

    def test_share_endpoint_requires_auth(self, api_factory, repository):
        """Test that share management endpoints require authentication."""
        from explorer.views import repository_share_view

        request = api_factory.post(f"/api/repositories/{repository.id}/share/")
        # No authentication
        response = repository_share_view(request, repository_id=repository.id)

        # DRF returns 401 or 403 for unauthenticated requests depending on auth backend
        assert response.status_code in (401, 403)

    def test_share_endpoint_forbidden_for_non_owner(
        self, api_factory, repository, db
    ):
        """Test that non-owners cannot manage sharing."""
        from explorer.views import repository_share_view

        other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="otherpass123",
        )

        request = api_factory.post(f"/api/repositories/{repository.id}/share/")
        force_authenticate(request, user=other_user)
        response = repository_share_view(request, repository_id=repository.id)

        assert response.status_code == 403

    def test_share_endpoint_repository_not_found(self, api_factory, user):
        """Test that share endpoint returns 404 for non-existent repository."""
        from explorer.views import repository_share_view

        request = api_factory.post("/api/repositories/99999/share/")
        force_authenticate(request, user=user)
        response = repository_share_view(request, repository_id=99999)

        assert response.status_code == 404

    def test_shared_view_attribution_banner(self, api_factory, user, repository):
        """Test that shared view includes attribution with owner username."""
        from explorer.views import shared_repository_view

        shared_view = SharingService().enable_sharing(repository)

        request = api_factory.get(f"/api/shared/{shared_view.token}/")
        response = shared_repository_view(request, token=shared_view.token)

        assert response.status_code == 200
        assert response.data["owner_username"] == "testuser"
        assert "testuser" in response.data["attribution"]
