"""
Unit tests for MVP hard caps and usage tracking.

Tests cover:
- 3 repositories per user limit (GitHub and ZIP ingestion)
- 200 files per repository limit (clone task and ZIP extraction)
- Usage tracking (repos created, files processed)
- Branding watermark on shared views
"""

from unittest.mock import MagicMock, patch

import pytest

from explorer.ingestion import (
    IngestionService,
    MAX_FILES_PER_REPO,
    MAX_REPOS_PER_USER,
    RepoLimitExceededError,
    extract_zip_task,
)
from explorer.models import Repository, SharedView, UsageStats, User
from explorer.tasks import clone_repository_task


@pytest.fixture
def encryption_service_mock():
    """Mock the TokenEncryptionService."""
    with patch("explorer.ingestion.TokenEncryptionService") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.decrypt.return_value = "ghp_test_token_123"
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def user_with_token(db):
    """Create a user with an encrypted GitHub token."""
    user = User.objects.create_user(
        username="limituser",
        email="limit@example.com",
        password="testpass123",
    )
    user.github_token_encrypted = b"encrypted_token_data"
    user.save()
    return user


@pytest.fixture
def github_repo_response():
    """Sample GitHub API response for a repository."""
    return {
        "name": "new-repo",
        "full_name": "owner/new-repo",
        "size": 1024,  # 1 MB in KB
        "default_branch": "main",
        "private": False,
    }


class TestRepoLimitGitHub:
    """Tests for the 3 repositories per user limit on GitHub ingestion."""

    @patch("explorer.ingestion.requests.get")
    def test_rejects_when_limit_reached(
        self, mock_get, user_with_token, encryption_service_mock
    ):
        """Test that ingestion is rejected when user has 3 repos."""
        # Create 3 existing repositories
        for i in range(3):
            Repository.objects.create(
                user=user_with_token,
                name=f"repo-{i}",
                source_type="github",
                github_full_name=f"owner/repo-{i}",
                status="ready",
            )

        service = IngestionService()

        with pytest.raises(RepoLimitExceededError, match="maximum limit of 3"):
            service.ingest_from_github(user_with_token, "owner/new-repo")

    @patch("explorer.ingestion.requests.get")
    def test_allows_ingestion_below_limit(
        self, mock_get, user_with_token, encryption_service_mock, github_repo_response
    ):
        """Test that ingestion is allowed when user has fewer than 3 repos."""
        # Create 2 existing repositories
        for i in range(2):
            Repository.objects.create(
                user=user_with_token,
                name=f"repo-{i}",
                source_type="github",
                github_full_name=f"owner/repo-{i}",
                status="ready",
            )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = github_repo_response
        mock_get.return_value = mock_response

        service = IngestionService()

        with patch("explorer.tasks.clone_repository_task.delay"):
            repo = service.ingest_from_github(user_with_token, "owner/new-repo")

        assert repo.status == "cloning"

    @patch("explorer.ingestion.requests.get")
    def test_allows_reingest_at_limit(
        self, mock_get, user_with_token, encryption_service_mock, github_repo_response
    ):
        """Test that re-ingestion is allowed even when at the limit."""
        # Create 3 existing repositories, one of which is the target
        for i in range(2):
            Repository.objects.create(
                user=user_with_token,
                name=f"repo-{i}",
                source_type="github",
                github_full_name=f"owner/repo-{i}",
                status="ready",
            )
        Repository.objects.create(
            user=user_with_token,
            name="new-repo",
            source_type="github",
            github_full_name="owner/new-repo",
            status="ready",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = github_repo_response
        mock_get.return_value = mock_response

        service = IngestionService()

        with patch("explorer.tasks.clone_repository_task.delay"):
            repo = service.ingest_from_github(
                user_with_token, "owner/new-repo", force_reingest=True
            )

        assert repo.status == "cloning"

    def test_error_message_is_clear(self):
        """Test that the error message clearly states the limit."""
        error = RepoLimitExceededError()
        assert "3" in str(error)
        assert "maximum limit" in str(error)


class TestRepoLimitZip:
    """Tests for the 3 repositories per user limit on ZIP ingestion."""

    def test_rejects_zip_when_limit_reached(self, user_with_token, encryption_service_mock):
        """Test that ZIP ingestion is rejected when user has 3 repos."""
        # Create 3 existing repositories
        for i in range(3):
            Repository.objects.create(
                user=user_with_token,
                name=f"repo-{i}",
                source_type="zip",
                status="ready",
            )

        service = IngestionService()

        # Create a minimal valid ZIP file mock
        zip_file = MagicMock()
        zip_file.size = 1024
        zip_file.read.return_value = b"PK\x03\x04"
        zip_file.seek = MagicMock()

        with pytest.raises(RepoLimitExceededError, match="maximum limit of 3"):
            service.ingest_from_zip(user_with_token, zip_file)


class TestFileCapGitHub:
    """Tests for the 200 files per repository limit on GitHub clone."""

    @patch("explorer.tasks.parse_repository_task.delay")
    @patch("explorer.tasks._get_redis_client")
    @patch("explorer.tasks.TokenEncryptionService")
    @patch("explorer.tasks.requests.get")
    def test_caps_files_at_200(
        self, mock_get, mock_enc_cls, mock_redis, mock_parse_task, user_with_token, db
    ):
        """Test that clone task only processes first 200 files."""
        mock_enc = MagicMock()
        mock_enc.decrypt.return_value = "ghp_test_token"
        mock_enc_cls.return_value = mock_enc

        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        repo = Repository.objects.create(
            user=user_with_token,
            name="big-repo",
            source_type="github",
            github_full_name="owner/big-repo",
            status="cloning",
        )

        # Create a tree with 250 files
        large_tree = [
            {"path": f"src/file{i}.py", "type": "blob", "size": 100, "sha": f"sha{i}"}
            for i in range(250)
        ]

        def mock_get_side_effect(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()

            if "/commits/" in url:
                resp.json.return_value = {"sha": "abc123"}
            elif "/git/trees/" in url:
                resp.json.return_value = {"tree": large_tree}
            elif "/git/blobs/" in url:
                resp.content = b"print('hello')"
            else:
                resp.json.return_value = {"default_branch": "main", "size": 100}

            return resp

        mock_get.side_effect = mock_get_side_effect

        clone_repository_task(repo.id, user_with_token.id)

        repo.refresh_from_db()
        assert repo.status == "parsing"
        assert repo.file_count == MAX_FILES_PER_REPO  # 200, not 250

    @patch("explorer.tasks.parse_repository_task.delay")
    @patch("explorer.tasks._get_redis_client")
    @patch("explorer.tasks.TokenEncryptionService")
    @patch("explorer.tasks.requests.get")
    def test_processes_all_files_below_cap(
        self, mock_get, mock_enc_cls, mock_redis, mock_parse_task, user_with_token, db
    ):
        """Test that all files are processed when below the 200 cap."""
        mock_enc = MagicMock()
        mock_enc.decrypt.return_value = "ghp_test_token"
        mock_enc_cls.return_value = mock_enc

        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        repo = Repository.objects.create(
            user=user_with_token,
            name="small-repo",
            source_type="github",
            github_full_name="owner/small-repo",
            status="cloning",
        )

        # Create a tree with 50 files
        small_tree = [
            {"path": f"src/file{i}.py", "type": "blob", "size": 100, "sha": f"sha{i}"}
            for i in range(50)
        ]

        def mock_get_side_effect(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()

            if "/commits/" in url:
                resp.json.return_value = {"sha": "abc123"}
            elif "/git/trees/" in url:
                resp.json.return_value = {"tree": small_tree}
            elif "/git/blobs/" in url:
                resp.content = b"print('hello')"
            else:
                resp.json.return_value = {"default_branch": "main", "size": 100}

            return resp

        mock_get.side_effect = mock_get_side_effect

        clone_repository_task(repo.id, user_with_token.id)

        repo.refresh_from_db()
        assert repo.file_count == 50


class TestUsageTracking:
    """Tests for usage tracking (repos created, files processed)."""

    @patch("explorer.ingestion.requests.get")
    def test_github_ingestion_increments_repos_created(
        self, mock_get, user_with_token, encryption_service_mock, github_repo_response
    ):
        """Test that GitHub ingestion increments repos_created."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = github_repo_response
        mock_get.return_value = mock_response

        service = IngestionService()

        with patch("explorer.tasks.clone_repository_task.delay"):
            service.ingest_from_github(user_with_token, "owner/new-repo")

        stats = UsageStats.objects.get(user=user_with_token)
        assert stats.repos_created == 1

    @patch("explorer.ingestion.requests.get")
    def test_multiple_ingestions_increment_counter(
        self, mock_get, user_with_token, encryption_service_mock, github_repo_response
    ):
        """Test that multiple ingestions increment the counter correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = github_repo_response
        mock_get.return_value = mock_response

        service = IngestionService()

        with patch("explorer.tasks.clone_repository_task.delay"):
            service.ingest_from_github(user_with_token, "owner/new-repo")

        # Change the repo name for second ingestion
        github_repo_response["name"] = "second-repo"
        github_repo_response["full_name"] = "owner/second-repo"
        mock_response.json.return_value = github_repo_response

        with patch("explorer.tasks.clone_repository_task.delay"):
            service.ingest_from_github(user_with_token, "owner/second-repo")

        stats = UsageStats.objects.get(user=user_with_token)
        assert stats.repos_created == 2

    @patch("explorer.tasks.parse_repository_task.delay")
    @patch("explorer.tasks._get_redis_client")
    @patch("explorer.tasks.TokenEncryptionService")
    @patch("explorer.tasks.requests.get")
    def test_clone_task_tracks_files_processed(
        self, mock_get, mock_enc_cls, mock_redis, mock_parse_task, user_with_token, db
    ):
        """Test that clone task updates files_processed in usage stats."""
        mock_enc = MagicMock()
        mock_enc.decrypt.return_value = "ghp_test_token"
        mock_enc_cls.return_value = mock_enc

        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        repo = Repository.objects.create(
            user=user_with_token,
            name="test-repo",
            source_type="github",
            github_full_name="owner/test-repo",
            status="cloning",
        )

        tree = [
            {"path": f"file{i}.py", "type": "blob", "size": 100, "sha": f"sha{i}"}
            for i in range(5)
        ]

        def mock_get_side_effect(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()

            if "/commits/" in url:
                resp.json.return_value = {"sha": "abc123"}
            elif "/git/trees/" in url:
                resp.json.return_value = {"tree": tree}
            elif "/git/blobs/" in url:
                resp.content = b"print('hello')"
            else:
                resp.json.return_value = {"default_branch": "main", "size": 100}

            return resp

        mock_get.side_effect = mock_get_side_effect

        clone_repository_task(repo.id, user_with_token.id)

        stats = UsageStats.objects.get(user=user_with_token)
        assert stats.files_processed == 5

    def test_usage_stats_model_creation(self, user_with_token):
        """Test that UsageStats model can be created with defaults."""
        stats = UsageStats.objects.create(user=user_with_token)
        assert stats.repos_created == 0
        assert stats.files_processed == 0
        assert stats.summaries_generated == 0


class TestBrandingWatermark:
    """Tests for the branding watermark on shared views."""

    def test_shared_view_includes_branding(self, user_with_token, db):
        """Test that shared repository view response includes branding."""
        from rest_framework.test import APIRequestFactory
        from explorer.views import shared_repository_view

        # Create a repository with a shared view
        repo = Repository.objects.create(
            user=user_with_token,
            name="shared-repo",
            source_type="github",
            github_full_name="owner/shared-repo",
            status="ready",
        )
        shared_view = SharedView.objects.create(
            repository=repo,
            token="test-token-abcdefghijklmnop",
            is_active=True,
        )

        factory = APIRequestFactory()
        request = factory.get(f"/api/shared/{shared_view.token}/")

        response = shared_repository_view(request, shared_view.token)

        assert response.status_code == 200
        assert "branding" in response.data
        assert "Powered by" in response.data["branding"]

    def test_shared_view_branding_value(self, user_with_token, db):
        """Test the exact branding watermark value."""
        from rest_framework.test import APIRequestFactory
        from explorer.views import shared_repository_view

        repo = Repository.objects.create(
            user=user_with_token,
            name="branded-repo",
            source_type="github",
            github_full_name="owner/branded-repo",
            status="ready",
        )
        shared_view = SharedView.objects.create(
            repository=repo,
            token="brand-token-abcdefghijklmnop",
            is_active=True,
        )

        factory = APIRequestFactory()
        request = factory.get(f"/api/shared/{shared_view.token}/")

        response = shared_repository_view(request, shared_view.token)

        assert response.data["branding"] == "Powered by DevConnPf"
