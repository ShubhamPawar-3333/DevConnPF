"""
Unit tests for the GitHub repository ingestion service and Celery task.

Tests cover:
- Token validation and permission checking
- Repository size limit enforcement
- Re-ingestion handling
- Clone task execution with mocked GitHub API
- Timeout handling
- Network error handling
- Progress updates in Redis
"""

from unittest.mock import MagicMock, patch

import pytest

from explorer.ingestion import (
    IngestionError,
    IngestionService,
    MAX_REPO_SIZE_BYTES,
    RepoAlreadyExistsError,
    RepoSizeExceededError,
    TokenPermissionError,
)
from explorer.models import Repository, RepositoryFile, User
from explorer.tasks import (
    clone_repository_task,
    _detect_language_from_extension,
    _is_summarizable,
)


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
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )
    user.github_token_encrypted = b"encrypted_token_data"
    user.save()
    return user


@pytest.fixture
def user_without_token(db):
    """Create a user without a GitHub token."""
    return User.objects.create_user(
        username="notokenuser",
        email="notoken@example.com",
        password="testpass123",
    )


@pytest.fixture
def github_repo_response():
    """Sample GitHub API response for a repository."""
    return {
        "name": "my-repo",
        "full_name": "owner/my-repo",
        "size": 1024,  # 1 MB in KB (GitHub reports in KB)
        "default_branch": "main",
        "private": False,
    }


@pytest.fixture
def large_repo_response():
    """Sample GitHub API response for a repository exceeding size limit."""
    return {
        "name": "huge-repo",
        "full_name": "owner/huge-repo",
        "size": 600 * 1024,  # 600 MB in KB
        "default_branch": "main",
        "private": False,
    }


class TestIngestionService:
    """Tests for IngestionService.ingest_from_github()."""

    @patch("explorer.ingestion.requests.get")
    def test_ingest_creates_repository_record(
        self, mock_get, user_with_token, encryption_service_mock, github_repo_response
    ):
        """Test that ingest_from_github creates a Repository with status 'cloning'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = github_repo_response
        mock_get.return_value = mock_response

        service = IngestionService()

        with patch("explorer.tasks.clone_repository_task.delay") as mock_task:
            repo = service.ingest_from_github(user_with_token, "owner/my-repo")

        assert repo.name == "my-repo"
        assert repo.source_type == "github"
        assert repo.github_full_name == "owner/my-repo"
        assert repo.status == "cloning"
        assert repo.user == user_with_token

    @patch("explorer.ingestion.requests.get")
    def test_ingest_dispatches_clone_task(
        self, mock_get, user_with_token, encryption_service_mock, github_repo_response
    ):
        """Test that ingest_from_github dispatches the clone_repository_task."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = github_repo_response
        mock_get.return_value = mock_response

        service = IngestionService()

        with patch("explorer.tasks.clone_repository_task.delay") as mock_task:
            repo = service.ingest_from_github(user_with_token, "owner/my-repo")
            mock_task.assert_called_once_with(repo.id, user_with_token.id)

    def test_ingest_raises_error_without_token(
        self, user_without_token, encryption_service_mock
    ):
        """Test that ingest_from_github raises IngestionError if user has no token."""
        service = IngestionService()

        with pytest.raises(IngestionError, match="No GitHub token found"):
            service.ingest_from_github(user_without_token, "owner/my-repo")

    @patch("explorer.ingestion.requests.get")
    def test_ingest_rejects_oversized_repo(
        self, mock_get, user_with_token, encryption_service_mock, large_repo_response
    ):
        """Test that ingest_from_github rejects repos > 500 MB."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = large_repo_response
        mock_get.return_value = mock_response

        service = IngestionService()

        with pytest.raises(RepoSizeExceededError):
            service.ingest_from_github(user_with_token, "owner/huge-repo")

    @patch("explorer.ingestion.requests.get")
    def test_ingest_raises_on_401(
        self, mock_get, user_with_token, encryption_service_mock
    ):
        """Test that a 401 response raises TokenPermissionError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        service = IngestionService()

        with pytest.raises(TokenPermissionError, match="invalid or expired"):
            service.ingest_from_github(user_with_token, "owner/my-repo")

    @patch("explorer.ingestion.requests.get")
    def test_ingest_raises_on_403(
        self, mock_get, user_with_token, encryption_service_mock
    ):
        """Test that a 403 response raises TokenPermissionError."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        service = IngestionService()

        with pytest.raises(TokenPermissionError, match="lacks the required permissions"):
            service.ingest_from_github(user_with_token, "owner/my-repo")

    @patch("explorer.ingestion.requests.get")
    def test_ingest_raises_on_404(
        self, mock_get, user_with_token, encryption_service_mock
    ):
        """Test that a 404 response raises TokenPermissionError."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        service = IngestionService()

        with pytest.raises(TokenPermissionError, match="not found"):
            service.ingest_from_github(user_with_token, "owner/my-repo")

    @patch("explorer.ingestion.requests.get")
    def test_ingest_raises_on_network_error(
        self, mock_get, user_with_token, encryption_service_mock
    ):
        """Test that network errors raise IngestionError."""
        import requests as req

        mock_get.side_effect = req.ConnectionError("Connection refused")

        service = IngestionService()

        with pytest.raises(IngestionError, match="Failed to connect"):
            service.ingest_from_github(user_with_token, "owner/my-repo")

    @patch("explorer.ingestion.requests.get")
    def test_ingest_raises_on_existing_repo(
        self, mock_get, user_with_token, encryption_service_mock, github_repo_response
    ):
        """Test that re-ingestion raises RepoAlreadyExistsError when not forced."""
        # Create an existing repository
        Repository.objects.create(
            user=user_with_token,
            name="my-repo",
            source_type="github",
            github_full_name="owner/my-repo",
            status="ready",
        )

        service = IngestionService()

        with pytest.raises(RepoAlreadyExistsError):
            service.ingest_from_github(user_with_token, "owner/my-repo")

    @patch("explorer.ingestion.requests.get")
    def test_ingest_force_reingest_deletes_old(
        self, mock_get, user_with_token, encryption_service_mock, github_repo_response
    ):
        """Test that force_reingest=True deletes old data and creates new record."""
        # Create an existing repository
        old_repo = Repository.objects.create(
            user=user_with_token,
            name="my-repo",
            source_type="github",
            github_full_name="owner/my-repo",
            status="ready",
        )
        old_id = old_repo.id

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = github_repo_response
        mock_get.return_value = mock_response

        service = IngestionService()

        with patch("explorer.tasks.clone_repository_task.delay"):
            repo = service.ingest_from_github(
                user_with_token, "owner/my-repo", force_reingest=True
            )

        assert repo.id != old_id
        assert repo.status == "cloning"
        assert not Repository.objects.filter(id=old_id).exists()


class TestCloneRepositoryTask:
    """Tests for the clone_repository_task Celery task."""

    @patch("explorer.tasks.parse_repository_task.delay")
    @patch("explorer.tasks._get_redis_client")
    @patch("explorer.tasks.TokenEncryptionService")
    @patch("explorer.tasks.requests.get")
    def test_clone_stores_files(
        self, mock_get, mock_enc_cls, mock_redis, mock_parse_task, user_with_token, db
    ):
        """Test that clone_repository_task fetches and stores files."""
        # Setup encryption mock
        mock_enc = MagicMock()
        mock_enc.decrypt.return_value = "ghp_test_token"
        mock_enc_cls.return_value = mock_enc

        # Setup Redis mock
        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        # Create repository
        repo = Repository.objects.create(
            user=user_with_token,
            name="test-repo",
            source_type="github",
            github_full_name="owner/test-repo",
            status="cloning",
        )

        # Mock GitHub API responses
        def mock_get_side_effect(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()

            if "/commits/" in url:
                resp.json.return_value = {"sha": "abc123def456"}
            elif "/git/trees/" in url:
                resp.json.return_value = {
                    "tree": [
                        {"path": "src/main.py", "type": "blob", "size": 500, "sha": "blob1"},
                        {"path": "README.md", "type": "blob", "size": 200, "sha": "blob2"},
                        {"path": "src", "type": "tree", "size": 0, "sha": "tree1"},
                    ]
                }
            elif "/git/blobs/" in url:
                resp.content = b"print('hello world')"
            else:
                resp.json.return_value = {
                    "default_branch": "main",
                    "size": 100,
                }

            return resp

        mock_get.side_effect = mock_get_side_effect

        # Execute the task synchronously
        clone_repository_task(repo.id, user_with_token.id)

        # Verify repository was updated
        repo.refresh_from_db()
        assert repo.status == "parsing"
        assert repo.branch == "main"
        assert repo.commit_sha == "abc123def456"
        assert repo.file_count == 2  # 2 blobs, 1 tree (excluded)
        assert repo.total_size_bytes == 700  # 500 + 200

        # Verify files were stored
        files = RepositoryFile.objects.filter(repository=repo)
        assert files.count() == 2
        assert files.filter(path="src/main.py").exists()
        assert files.filter(path="README.md").exists()

        # Verify parse_repository_task was dispatched
        mock_parse_task.assert_called_once_with(repo.id)

    @patch("explorer.tasks._get_redis_client")
    @patch("explorer.tasks.TokenEncryptionService")
    @patch("explorer.tasks.requests.get")
    def test_clone_handles_timeout(
        self, mock_get, mock_enc_cls, mock_redis, user_with_token, db
    ):
        """Test that clone_repository_task handles SoftTimeLimitExceeded."""
        from celery.exceptions import SoftTimeLimitExceeded

        mock_enc = MagicMock()
        mock_enc.decrypt.return_value = "ghp_test_token"
        mock_enc_cls.return_value = mock_enc

        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        repo = Repository.objects.create(
            user=user_with_token,
            name="slow-repo",
            source_type="github",
            github_full_name="owner/slow-repo",
            status="cloning",
        )

        # Simulate timeout during API call
        mock_get.side_effect = SoftTimeLimitExceeded()

        clone_repository_task(repo.id, user_with_token.id)

        repo.refresh_from_db()
        assert repo.status == "failed"

    @patch("explorer.tasks._get_redis_client")
    @patch("explorer.tasks.TokenEncryptionService")
    @patch("explorer.tasks.requests.get")
    def test_clone_handles_network_error(
        self, mock_get, mock_enc_cls, mock_redis, user_with_token, db
    ):
        """Test that clone_repository_task handles network errors."""
        import requests as req

        mock_enc = MagicMock()
        mock_enc.decrypt.return_value = "ghp_test_token"
        mock_enc_cls.return_value = mock_enc

        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        repo = Repository.objects.create(
            user=user_with_token,
            name="unreachable-repo",
            source_type="github",
            github_full_name="owner/unreachable-repo",
            status="cloning",
        )

        mock_get.side_effect = req.ConnectionError("Connection refused")

        clone_repository_task(repo.id, user_with_token.id)

        repo.refresh_from_db()
        assert repo.status == "failed"

    @patch("explorer.tasks._get_redis_client")
    @patch("explorer.tasks.TokenEncryptionService")
    @patch("explorer.tasks.requests.get")
    def test_clone_rejects_oversized_repo_during_tree_fetch(
        self, mock_get, mock_enc_cls, mock_redis, user_with_token, db
    ):
        """Test that clone task rejects repos exceeding 500 MB during tree fetch."""
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

        # Create a tree with files totaling > 500 MB
        large_tree = [
            {"path": f"file{i}.bin", "type": "blob", "size": 100 * 1024 * 1024, "sha": f"sha{i}"}
            for i in range(6)  # 6 * 100 MB = 600 MB
        ]

        def mock_get_side_effect(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()

            if "/commits/" in url:
                resp.json.return_value = {"sha": "abc123"}
            elif "/git/trees/" in url:
                resp.json.return_value = {"tree": large_tree}
            else:
                resp.json.return_value = {"default_branch": "main", "size": 600000}

            return resp

        mock_get.side_effect = mock_get_side_effect

        clone_repository_task(repo.id, user_with_token.id)

        repo.refresh_from_db()
        assert repo.status == "failed"


class TestHelperFunctions:
    """Tests for helper functions in the tasks module."""

    def test_detect_language_python(self):
        assert _detect_language_from_extension("main.py") == "python"

    def test_detect_language_javascript(self):
        assert _detect_language_from_extension("app.js") == "javascript"

    def test_detect_language_typescript(self):
        assert _detect_language_from_extension("index.ts") == "typescript"

    def test_detect_language_unknown(self):
        assert _detect_language_from_extension("data.xyz") == "unknown"

    def test_is_summarizable_python(self):
        assert _is_summarizable("main.py") is True

    def test_is_summarizable_lockfile(self):
        assert _is_summarizable("package-lock.json") is False

    def test_is_summarizable_minified(self):
        assert _is_summarizable("app.min.js") is False

    def test_is_summarizable_binary(self):
        assert _is_summarizable("image.png") is False

    def test_is_summarizable_unknown_extension(self):
        assert _is_summarizable("data.xyz") is False

    def test_validate_repository_size_within_limit(self):
        assert IngestionService.validate_repository_size_static(100 * 1024 * 1024) is True

    def test_validate_repository_size_at_limit(self):
        assert IngestionService.validate_repository_size_static(MAX_REPO_SIZE_BYTES) is True

    def test_validate_repository_size_exceeds_limit(self):
        assert IngestionService.validate_repository_size_static(MAX_REPO_SIZE_BYTES + 1) is False
