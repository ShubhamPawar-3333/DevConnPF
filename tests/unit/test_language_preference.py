"""
Unit tests for the language preference and summary regeneration module.

Tests the PUT /api/users/me/language/ endpoint and
POST /api/repositories/{id}/regenerate-summaries/ endpoint.
"""

import pytest
from unittest.mock import patch
from django.test import RequestFactory
from rest_framework.test import force_authenticate

from explorer.models import (
    CodeBlock,
    Repository,
    RepositoryFile,
    SummarizationJob,
    User,
)
from explorer.views import language_preference_view, regenerate_summaries_view


@pytest.fixture
def user(db):
    """Create a test user with default language preference."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def other_user(db):
    """Create another test user for permission tests."""
    return User.objects.create_user(
        username="otheruser",
        email="other@example.com",
        password="otherpass123",
    )


@pytest.fixture
def repository(user):
    """Create a test repository."""
    return Repository.objects.create(
        user=user,
        name="test-repo",
        source_type="github",
        status="ready",
    )


@pytest.fixture
def repo_file(repository):
    """Create a test repository file."""
    return RepositoryFile.objects.create(
        repository=repository,
        path="src/main.py",
        filename="main.py",
        language="python",
        content="def hello(): pass",
        size_bytes=18,
        is_summarizable=True,
    )


@pytest.fixture
def non_summarizable_file(repository):
    """Create a non-summarizable file."""
    return RepositoryFile.objects.create(
        repository=repository,
        path="assets/logo.png",
        filename="logo.png",
        language="unknown",
        content="binary data",
        size_bytes=1024,
        is_summarizable=False,
    )


@pytest.fixture
def code_block(repo_file):
    """Create a test code block."""
    return CodeBlock.objects.create(
        file=repo_file,
        name="hello",
        kind="function",
        start_line=1,
        end_line=1,
        content="def hello(): pass",
    )


@pytest.fixture
def request_factory():
    """Create a Django request factory."""
    return RequestFactory()


class TestLanguagePreferenceView:
    """Tests for PUT /api/users/me/language/ endpoint."""

    def test_set_valid_language(self, request_factory, user):
        """Setting a valid language code updates the user's preference."""
        request = request_factory.put(
            "/api/users/me/language/",
            data={"language": "es"},
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = language_preference_view(request)

        assert response.status_code == 200
        assert response.data["language"] == "es"
        assert response.data["message"] == "Language preference updated."

        user.refresh_from_db()
        assert user.language_preference == "es"

    def test_set_all_supported_languages(self, request_factory, user):
        """All 8 supported language codes are accepted."""
        supported = ["en", "es", "fr", "de", "pt", "ja", "ko", "zh"]
        for lang in supported:
            request = request_factory.put(
                "/api/users/me/language/",
                data={"language": lang},
                content_type="application/json",
            )
            force_authenticate(request, user=user)

            response = language_preference_view(request)

            assert response.status_code == 200
            assert response.data["language"] == lang

    def test_invalid_language_code_returns_400(self, request_factory, user):
        """An unsupported language code returns 400."""
        request = request_factory.put(
            "/api/users/me/language/",
            data={"language": "xx"},
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = language_preference_view(request)

        assert response.status_code == 400
        assert "Unsupported language code" in response.data["error"]

    def test_missing_language_field_returns_400(self, request_factory, user):
        """Missing language field returns 400."""
        request = request_factory.put(
            "/api/users/me/language/",
            data={},
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = language_preference_view(request)

        assert response.status_code == 400
        assert "required" in response.data["error"].lower()

    def test_empty_language_returns_400(self, request_factory, user):
        """Empty string language returns 400."""
        request = request_factory.put(
            "/api/users/me/language/",
            data={"language": ""},
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = language_preference_view(request)

        assert response.status_code == 400

    def test_unauthenticated_returns_403(self, request_factory):
        """Unauthenticated request returns 403."""
        request = request_factory.put(
            "/api/users/me/language/",
            data={"language": "es"},
            content_type="application/json",
        )

        response = language_preference_view(request)

        assert response.status_code == 403

    def test_default_language_is_en(self, user):
        """User's default language preference is 'en'."""
        assert user.language_preference == "en"


class TestRegenerateSummariesView:
    """Tests for POST /api/repositories/{id}/regenerate-summaries/ endpoint."""

    @patch("explorer.views.summarize_file_task.delay")
    @patch("explorer.views.summarize_block_task.delay")
    def test_regeneration_enqueues_jobs(
        self, mock_block_task, mock_file_task, request_factory, user, repository, repo_file, code_block
    ):
        """Regeneration creates new jobs and dispatches Celery tasks."""
        request = request_factory.post(
            f"/api/repositories/{repository.id}/regenerate-summaries/",
        )
        force_authenticate(request, user=user)

        response = regenerate_summaries_view(request, repository_id=repository.id)

        assert response.status_code == 202
        assert response.data["jobs_enqueued"] == 2  # 1 file + 1 block
        assert response.data["language"] == "en"
        mock_file_task.assert_called_once_with(repo_file.id, "en")
        mock_block_task.assert_called_once_with(code_block.id, "en")

    @patch("explorer.views.summarize_file_task.delay")
    @patch("explorer.views.summarize_block_task.delay")
    def test_regeneration_uses_user_language_preference(
        self, mock_block_task, mock_file_task, request_factory, user, repository, repo_file
    ):
        """Regeneration uses the user's current language preference."""
        user.language_preference = "ja"
        user.save(update_fields=["language_preference"])

        request = request_factory.post(
            f"/api/repositories/{repository.id}/regenerate-summaries/",
        )
        force_authenticate(request, user=user)

        response = regenerate_summaries_view(request, repository_id=repository.id)

        assert response.status_code == 202
        assert response.data["language"] == "ja"
        mock_file_task.assert_called_once_with(repo_file.id, "ja")

    @patch("explorer.views.summarize_file_task.delay")
    @patch("explorer.views.summarize_block_task.delay")
    def test_regeneration_deletes_old_jobs(
        self, mock_block_task, mock_file_task, request_factory, user, repository, repo_file
    ):
        """Regeneration deletes existing SummarizationJob records."""
        # Create existing jobs
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="completed",
        )

        request = request_factory.post(
            f"/api/repositories/{repository.id}/regenerate-summaries/",
        )
        force_authenticate(request, user=user)

        response = regenerate_summaries_view(request, repository_id=repository.id)

        assert response.status_code == 202
        # Old job should be deleted, new one created
        jobs = SummarizationJob.objects.filter(repository=repository)
        assert all(job.status == "pending" for job in jobs)

    @patch("explorer.views.summarize_file_task.delay")
    @patch("explorer.views.summarize_block_task.delay")
    def test_regeneration_sets_status_to_summarizing(
        self, mock_block_task, mock_file_task, request_factory, user, repository, repo_file
    ):
        """Regeneration updates repository status to 'summarizing'."""
        request = request_factory.post(
            f"/api/repositories/{repository.id}/regenerate-summaries/",
        )
        force_authenticate(request, user=user)

        response = regenerate_summaries_view(request, repository_id=repository.id)

        repository.refresh_from_db()
        assert repository.status == "summarizing"

    @patch("explorer.views.summarize_file_task.delay")
    @patch("explorer.views.summarize_block_task.delay")
    def test_regeneration_skips_non_summarizable_files(
        self, mock_block_task, mock_file_task, request_factory, user, repository, non_summarizable_file
    ):
        """Regeneration only enqueues jobs for summarizable files."""
        request = request_factory.post(
            f"/api/repositories/{repository.id}/regenerate-summaries/",
        )
        force_authenticate(request, user=user)

        response = regenerate_summaries_view(request, repository_id=repository.id)

        assert response.status_code == 202
        assert response.data["jobs_enqueued"] == 0
        mock_file_task.assert_not_called()
        mock_block_task.assert_not_called()

    def test_non_owner_gets_403(self, request_factory, other_user, repository):
        """Non-owner gets 403 Forbidden."""
        request = request_factory.post(
            f"/api/repositories/{repository.id}/regenerate-summaries/",
        )
        force_authenticate(request, user=other_user)

        response = regenerate_summaries_view(request, repository_id=repository.id)

        assert response.status_code == 403

    def test_nonexistent_repository_gets_404(self, request_factory, user):
        """Non-existent repository returns 404."""
        request = request_factory.post("/api/repositories/99999/regenerate-summaries/")
        force_authenticate(request, user=user)

        response = regenerate_summaries_view(request, repository_id=99999)

        assert response.status_code == 404

    def test_unauthenticated_gets_403(self, request_factory, repository):
        """Unauthenticated request returns 403."""
        request = request_factory.post(
            f"/api/repositories/{repository.id}/regenerate-summaries/",
        )

        response = regenerate_summaries_view(request, repository_id=repository.id)

        assert response.status_code == 403
