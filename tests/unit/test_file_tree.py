"""
Unit tests for the file tree browser API endpoints.

Tests the repository tree view, file detail view, and block detail view
including ownership checks, sort order, summary status, and retry options.
"""

import pytest
from django.test import RequestFactory
from rest_framework.test import force_authenticate

from explorer.models import (
    BlockSummary,
    CodeBlock,
    FileSummary,
    Repository,
    RepositoryFile,
    User,
)
from explorer.views import (
    block_detail_view,
    file_detail_view,
    repository_tree_view,
    sort_tree_entries,
)


@pytest.fixture
def user(db):
    """Create a test user."""
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
def request_factory():
    """Create a Django request factory."""
    return RequestFactory()


class TestSortTreeEntries:
    """Tests for the sort_tree_entries helper function."""

    def test_directories_before_files(self):
        """Directories should appear before files."""
        entries = [
            {"name": "main.py", "type": "file"},
            {"name": "src", "type": "directory"},
            {"name": "README.md", "type": "file"},
            {"name": "docs", "type": "directory"},
        ]
        result = sort_tree_entries(entries)
        types = [e["type"] for e in result]
        assert types == ["directory", "directory", "file", "file"]

    def test_alphabetical_case_insensitive(self):
        """Entries should be sorted alphabetically, case-insensitive."""
        entries = [
            {"name": "Zebra", "type": "directory"},
            {"name": "alpha", "type": "directory"},
            {"name": "Beta", "type": "directory"},
        ]
        result = sort_tree_entries(entries)
        names = [e["name"] for e in result]
        assert names == ["alpha", "Beta", "Zebra"]

    def test_files_sorted_alphabetically(self):
        """Files should be sorted alphabetically, case-insensitive."""
        entries = [
            {"name": "utils.py", "type": "file"},
            {"name": "App.js", "type": "file"},
            {"name": "main.py", "type": "file"},
        ]
        result = sort_tree_entries(entries)
        names = [e["name"] for e in result]
        assert names == ["App.js", "main.py", "utils.py"]

    def test_empty_list(self):
        """Empty list returns empty list."""
        assert sort_tree_entries([]) == []

    def test_only_directories(self):
        """List with only directories sorts alphabetically."""
        entries = [
            {"name": "src", "type": "directory"},
            {"name": "docs", "type": "directory"},
            {"name": "tests", "type": "directory"},
        ]
        result = sort_tree_entries(entries)
        names = [e["name"] for e in result]
        assert names == ["docs", "src", "tests"]


class TestRepositoryTreeView:
    """Tests for GET /api/repositories/{id}/tree/ endpoint."""

    def test_authenticated_owner_gets_tree(self, request_factory, user, repository):
        """Authenticated owner can access their repository's tree."""
        RepositoryFile.objects.create(
            repository=repository,
            path="main.py",
            filename="main.py",
            language="python",
            content="print('hello')",
            size_bytes=14,
        )

        request = request_factory.get(f"/api/repositories/{repository.id}/tree/")
        force_authenticate(request, user=user)

        response = repository_tree_view(request, repository_id=repository.id)

        assert response.status_code == 200
        assert response.data["repository_id"] == repository.id
        assert response.data["repository_name"] == "test-repo"
        assert len(response.data["tree"]) == 1
        assert response.data["tree"][0]["name"] == "main.py"
        assert response.data["tree"][0]["type"] == "file"

    def test_non_owner_gets_403(self, request_factory, other_user, repository):
        """Non-owner gets 403 Forbidden."""
        request = request_factory.get(f"/api/repositories/{repository.id}/tree/")
        force_authenticate(request, user=other_user)

        response = repository_tree_view(request, repository_id=repository.id)

        assert response.status_code == 403

    def test_nonexistent_repository_gets_404(self, request_factory, user):
        """Non-existent repository returns 404."""
        request = request_factory.get("/api/repositories/99999/tree/")
        force_authenticate(request, user=user)

        response = repository_tree_view(request, repository_id=99999)

        assert response.status_code == 404

    def test_tree_with_nested_directories(self, request_factory, user, repository):
        """Tree correctly nests files in directories."""
        RepositoryFile.objects.create(
            repository=repository,
            path="src/utils/helpers.py",
            filename="helpers.py",
            language="python",
            content="def helper(): pass",
            size_bytes=18,
        )
        RepositoryFile.objects.create(
            repository=repository,
            path="src/main.py",
            filename="main.py",
            language="python",
            content="import helpers",
            size_bytes=14,
        )
        RepositoryFile.objects.create(
            repository=repository,
            path="README.md",
            filename="README.md",
            language="markdown",
            content="# Readme",
            size_bytes=8,
        )

        request = request_factory.get(f"/api/repositories/{repository.id}/tree/")
        force_authenticate(request, user=user)

        response = repository_tree_view(request, repository_id=repository.id)

        assert response.status_code == 200
        tree = response.data["tree"]

        # Root should have: src/ directory first, then README.md file
        assert len(tree) == 2
        assert tree[0]["type"] == "directory"
        assert tree[0]["name"] == "src"
        assert tree[1]["type"] == "file"
        assert tree[1]["name"] == "README.md"

        # src/ should have: utils/ directory first, then main.py file
        src_children = tree[0]["children"]
        assert len(src_children) == 2
        assert src_children[0]["type"] == "directory"
        assert src_children[0]["name"] == "utils"
        assert src_children[1]["type"] == "file"
        assert src_children[1]["name"] == "main.py"

    def test_summary_preview_truncated_at_80_chars(
        self, request_factory, user, repository
    ):
        """File summary preview is truncated at 80 characters."""
        file_obj = RepositoryFile.objects.create(
            repository=repository,
            path="main.py",
            filename="main.py",
            language="python",
            content="print('hello')",
            size_bytes=14,
        )
        long_summary = "A" * 200
        FileSummary.objects.create(
            file=file_obj,
            summary_text=long_summary,
            status="completed",
            language="en",
        )

        request = request_factory.get(f"/api/repositories/{repository.id}/tree/")
        force_authenticate(request, user=user)

        response = repository_tree_view(request, repository_id=repository.id)

        preview = response.data["tree"][0]["summary_preview"]
        assert len(preview) == 80
        assert preview.endswith("...")

    def test_summary_status_included(self, request_factory, user, repository):
        """Each file entry includes summary_status field."""
        file_obj = RepositoryFile.objects.create(
            repository=repository,
            path="main.py",
            filename="main.py",
            language="python",
            content="print('hello')",
            size_bytes=14,
        )
        FileSummary.objects.create(
            file=file_obj,
            summary_text="A summary",
            status="completed",
            language="en",
        )

        request = request_factory.get(f"/api/repositories/{repository.id}/tree/")
        force_authenticate(request, user=user)

        response = repository_tree_view(request, repository_id=repository.id)

        assert response.data["tree"][0]["summary_status"] == "completed"

    def test_pending_file_has_no_preview(self, request_factory, user, repository):
        """Files with pending summary have empty preview."""
        file_obj = RepositoryFile.objects.create(
            repository=repository,
            path="main.py",
            filename="main.py",
            language="python",
            content="print('hello')",
            size_bytes=14,
        )
        FileSummary.objects.create(
            file=file_obj,
            summary_text="",
            status="pending",
            language="en",
        )

        request = request_factory.get(f"/api/repositories/{repository.id}/tree/")
        force_authenticate(request, user=user)

        response = repository_tree_view(request, repository_id=repository.id)

        assert response.data["tree"][0]["summary_preview"] == ""
        assert response.data["tree"][0]["summary_status"] == "pending"

    def test_failed_file_has_retry_option(self, request_factory, user, repository):
        """Files with failed summary have can_retry=True."""
        file_obj = RepositoryFile.objects.create(
            repository=repository,
            path="main.py",
            filename="main.py",
            language="python",
            content="print('hello')",
            size_bytes=14,
        )
        FileSummary.objects.create(
            file=file_obj,
            summary_text="",
            status="failed",
            language="en",
        )

        request = request_factory.get(f"/api/repositories/{repository.id}/tree/")
        force_authenticate(request, user=user)

        response = repository_tree_view(request, repository_id=repository.id)

        assert response.data["tree"][0]["can_retry"] is True
        assert response.data["tree"][0]["summary_status"] == "failed"


class TestFileDetailView:
    """Tests for GET /api/repositories/{id}/files/{file_id}/ endpoint."""

    def test_returns_file_with_summary(self, request_factory, user, repository):
        """Returns file info with full summary text."""
        file_obj = RepositoryFile.objects.create(
            repository=repository,
            path="src/main.py",
            filename="main.py",
            language="python",
            content="print('hello')",
            size_bytes=14,
        )
        FileSummary.objects.create(
            file=file_obj,
            summary_text="This file is the main entry point.",
            status="completed",
            language="en",
        )

        request = request_factory.get(
            f"/api/repositories/{repository.id}/files/{file_obj.id}/"
        )
        force_authenticate(request, user=user)

        response = file_detail_view(
            request, repository_id=repository.id, file_id=file_obj.id
        )

        assert response.status_code == 200
        assert response.data["id"] == file_obj.id
        assert response.data["path"] == "src/main.py"
        assert response.data["filename"] == "main.py"
        assert response.data["language"] == "python"
        assert response.data["summary"]["summary_text"] == "This file is the main entry point."
        assert response.data["summary"]["status"] == "completed"

    def test_returns_block_summaries(self, request_factory, user, repository):
        """Returns list of block summaries for the file."""
        file_obj = RepositoryFile.objects.create(
            repository=repository,
            path="main.py",
            filename="main.py",
            language="python",
            content="def hello(): pass\ndef world(): pass",
            size_bytes=35,
        )
        block = CodeBlock.objects.create(
            file=file_obj,
            name="hello",
            kind="function",
            start_line=1,
            end_line=1,
            content="def hello(): pass",
        )
        BlockSummary.objects.create(
            block=block,
            summary_text="Says hello",
            status="completed",
            language="en",
        )

        request = request_factory.get(
            f"/api/repositories/{repository.id}/files/{file_obj.id}/"
        )
        force_authenticate(request, user=user)

        response = file_detail_view(
            request, repository_id=repository.id, file_id=file_obj.id
        )

        assert response.status_code == 200
        assert len(response.data["blocks"]) == 1
        assert response.data["blocks"][0]["name"] == "hello"
        assert response.data["blocks"][0]["summary_text"] == "Says hello"
        assert response.data["blocks"][0]["summary_status"] == "completed"

    def test_non_owner_gets_403(self, request_factory, other_user, repository):
        """Non-owner gets 403 Forbidden."""
        file_obj = RepositoryFile.objects.create(
            repository=repository,
            path="main.py",
            filename="main.py",
            language="python",
            content="print('hello')",
            size_bytes=14,
        )

        request = request_factory.get(
            f"/api/repositories/{repository.id}/files/{file_obj.id}/"
        )
        force_authenticate(request, user=other_user)

        response = file_detail_view(
            request, repository_id=repository.id, file_id=file_obj.id
        )

        assert response.status_code == 403

    def test_file_not_in_repository_gets_404(self, request_factory, user, repository):
        """File not belonging to the repository returns 404."""
        other_repo = Repository.objects.create(
            user=user,
            name="other-repo",
            source_type="github",
            status="ready",
        )
        file_obj = RepositoryFile.objects.create(
            repository=other_repo,
            path="main.py",
            filename="main.py",
            language="python",
            content="print('hello')",
            size_bytes=14,
        )

        request = request_factory.get(
            f"/api/repositories/{repository.id}/files/{file_obj.id}/"
        )
        force_authenticate(request, user=user)

        response = file_detail_view(
            request, repository_id=repository.id, file_id=file_obj.id
        )

        assert response.status_code == 404

    def test_failed_summary_shows_retry(self, request_factory, user, repository):
        """File with failed summary has can_retry=True."""
        file_obj = RepositoryFile.objects.create(
            repository=repository,
            path="main.py",
            filename="main.py",
            language="python",
            content="print('hello')",
            size_bytes=14,
        )
        FileSummary.objects.create(
            file=file_obj,
            summary_text="",
            status="failed",
            language="en",
        )

        request = request_factory.get(
            f"/api/repositories/{repository.id}/files/{file_obj.id}/"
        )
        force_authenticate(request, user=user)

        response = file_detail_view(
            request, repository_id=repository.id, file_id=file_obj.id
        )

        assert response.status_code == 200
        assert response.data["can_retry"] is True
        assert response.data["summary"]["status"] == "failed"
        assert response.data["summary"]["summary_text"] is None


class TestBlockDetailView:
    """Tests for GET /api/repositories/{id}/blocks/{block_id}/ endpoint."""

    def test_returns_block_with_source_code(self, request_factory, user, repository):
        """Returns block info with source code and summary."""
        file_obj = RepositoryFile.objects.create(
            repository=repository,
            path="main.py",
            filename="main.py",
            language="python",
            content="def hello():\n    return 'hello'",
            size_bytes=30,
        )
        block = CodeBlock.objects.create(
            file=file_obj,
            name="hello",
            kind="function",
            start_line=1,
            end_line=2,
            content="def hello():\n    return 'hello'",
        )
        BlockSummary.objects.create(
            block=block,
            summary_text="Returns a greeting string.",
            status="completed",
            language="en",
        )

        request = request_factory.get(
            f"/api/repositories/{repository.id}/blocks/{block.id}/"
        )
        force_authenticate(request, user=user)

        response = block_detail_view(
            request, repository_id=repository.id, block_id=block.id
        )

        assert response.status_code == 200
        assert response.data["id"] == block.id
        assert response.data["name"] == "hello"
        assert response.data["kind"] == "function"
        assert response.data["source_code"] == "def hello():\n    return 'hello'"
        assert response.data["file_path"] == "main.py"
        assert response.data["file_id"] == file_obj.id
        assert response.data["summary"]["summary_text"] == "Returns a greeting string."
        assert response.data["summary"]["status"] == "completed"

    def test_non_owner_gets_403(self, request_factory, other_user, repository):
        """Non-owner gets 403 Forbidden."""
        file_obj = RepositoryFile.objects.create(
            repository=repository,
            path="main.py",
            filename="main.py",
            language="python",
            content="def hello(): pass",
            size_bytes=17,
        )
        block = CodeBlock.objects.create(
            file=file_obj,
            name="hello",
            kind="function",
            start_line=1,
            end_line=1,
            content="def hello(): pass",
        )

        request = request_factory.get(
            f"/api/repositories/{repository.id}/blocks/{block.id}/"
        )
        force_authenticate(request, user=other_user)

        response = block_detail_view(
            request, repository_id=repository.id, block_id=block.id
        )

        assert response.status_code == 403

    def test_block_not_in_repository_gets_404(self, request_factory, user, repository):
        """Block not belonging to the repository returns 404."""
        other_repo = Repository.objects.create(
            user=user,
            name="other-repo",
            source_type="github",
            status="ready",
        )
        file_obj = RepositoryFile.objects.create(
            repository=other_repo,
            path="main.py",
            filename="main.py",
            language="python",
            content="def hello(): pass",
            size_bytes=17,
        )
        block = CodeBlock.objects.create(
            file=file_obj,
            name="hello",
            kind="function",
            start_line=1,
            end_line=1,
            content="def hello(): pass",
        )

        request = request_factory.get(
            f"/api/repositories/{repository.id}/blocks/{block.id}/"
        )
        force_authenticate(request, user=user)

        response = block_detail_view(
            request, repository_id=repository.id, block_id=block.id
        )

        assert response.status_code == 404

    def test_block_without_summary(self, request_factory, user, repository):
        """Block without a summary returns pending status."""
        file_obj = RepositoryFile.objects.create(
            repository=repository,
            path="main.py",
            filename="main.py",
            language="python",
            content="def hello(): pass",
            size_bytes=17,
        )
        block = CodeBlock.objects.create(
            file=file_obj,
            name="hello",
            kind="function",
            start_line=1,
            end_line=1,
            content="def hello(): pass",
        )

        request = request_factory.get(
            f"/api/repositories/{repository.id}/blocks/{block.id}/"
        )
        force_authenticate(request, user=user)

        response = block_detail_view(
            request, repository_id=repository.id, block_id=block.id
        )

        assert response.status_code == 200
        assert response.data["summary"]["status"] == "pending"
        assert response.data["summary"]["summary_text"] is None
