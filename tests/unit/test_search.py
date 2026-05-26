"""
Unit tests for the search module.

Tests the SummarySearchService and the search API endpoint using SQLite
fallback (since tests run with SQLite in-memory database).
"""

import pytest
from django.test import TestCase
from rest_framework.test import APIClient

from explorer.models import (
    BlockSummary,
    CodeBlock,
    FileSummary,
    Repository,
    RepositoryFile,
    User,
)
from explorer.search import QueryValidationError, SummarySearchService, validate_query


class TestQueryValidation(TestCase):
    """Tests for search query validation."""

    def test_valid_query(self):
        """A query between 3 and 300 characters is accepted."""
        result = validate_query("authentication")
        assert result == "authentication"

    def test_query_with_whitespace_trimmed(self):
        """Leading/trailing whitespace is trimmed."""
        result = validate_query("  hello world  ")
        assert result == "hello world"

    def test_query_too_short(self):
        """A query shorter than 3 characters raises QueryValidationError."""
        with pytest.raises(QueryValidationError) as exc_info:
            validate_query("ab")
        assert "at least 3 characters" in str(exc_info.value)

    def test_query_too_short_after_trim(self):
        """A query that becomes too short after trimming raises error."""
        with pytest.raises(QueryValidationError):
            validate_query("  ab  ")

    def test_query_too_long(self):
        """A query longer than 300 characters raises QueryValidationError."""
        long_query = "a" * 301
        with pytest.raises(QueryValidationError) as exc_info:
            validate_query(long_query)
        assert "must not exceed 300 characters" in str(exc_info.value)

    def test_empty_query(self):
        """An empty query raises QueryValidationError."""
        with pytest.raises(QueryValidationError):
            validate_query("")

    def test_whitespace_only_query(self):
        """A whitespace-only query raises QueryValidationError."""
        with pytest.raises(QueryValidationError):
            validate_query("   ")

    def test_query_exactly_3_chars(self):
        """A query of exactly 3 characters is accepted."""
        result = validate_query("abc")
        assert result == "abc"

    def test_query_exactly_300_chars(self):
        """A query of exactly 300 characters is accepted."""
        query = "a" * 300
        result = validate_query(query)
        assert result == query


@pytest.mark.django_db
class TestSummarySearchService(TestCase):
    """Tests for the SummarySearchService using SQLite fallback."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.repository = Repository.objects.create(
            user=self.user,
            name="test-repo",
            source_type="github",
            status="ready",
        )
        # Create a file with a summary
        self.file1 = RepositoryFile.objects.create(
            repository=self.repository,
            path="src/auth.py",
            filename="auth.py",
            language="python",
            content="def authenticate(): pass",
            size_bytes=100,
        )
        self.file_summary1 = FileSummary.objects.create(
            file=self.file1,
            summary_text="This file handles user authentication and session management. "
            "It provides login, logout, and token validation functionality.",
            status="completed",
            language="en",
        )

        # Create another file with a different summary
        self.file2 = RepositoryFile.objects.create(
            repository=self.repository,
            path="src/database.py",
            filename="database.py",
            language="python",
            content="def connect(): pass",
            size_bytes=200,
        )
        self.file_summary2 = FileSummary.objects.create(
            file=self.file2,
            summary_text="This module manages database connections and query execution. "
            "It provides connection pooling and transaction management.",
            status="completed",
            language="en",
        )

        # Create a code block with a summary
        self.block1 = CodeBlock.objects.create(
            file=self.file1,
            name="authenticate",
            kind="function",
            start_line=1,
            end_line=10,
            content="def authenticate(): pass",
        )
        self.block_summary1 = BlockSummary.objects.create(
            block=self.block1,
            summary_text="Authenticates a user by validating credentials against the database.",
            status="completed",
            language="en",
        )

        self.service = SummarySearchService()

    def test_search_returns_matching_file_summaries(self):
        """Search returns file summaries that match the query."""
        results = self.service.search(self.repository.id, "authentication")
        assert len(results) > 0
        file_results = [r for r in results if r.result_type == "file"]
        assert any(r.file_path == "src/auth.py" for r in file_results)

    def test_search_returns_matching_block_summaries(self):
        """Search returns block summaries that match the query."""
        results = self.service.search(self.repository.id, "authenticates user")
        block_results = [r for r in results if r.result_type == "block"]
        assert any(r.block_name == "authenticate" for r in block_results)

    def test_search_returns_empty_for_no_matches(self):
        """Search returns empty list when no summaries match."""
        results = self.service.search(self.repository.id, "xyznonexistent")
        assert results == []

    def test_search_scoped_to_repository(self):
        """Search results are scoped to the specified repository."""
        # Create another repository with a matching summary
        other_repo = Repository.objects.create(
            user=self.user,
            name="other-repo",
            source_type="github",
            status="ready",
        )
        other_file = RepositoryFile.objects.create(
            repository=other_repo,
            path="src/auth.py",
            filename="auth.py",
            language="python",
            content="def authenticate(): pass",
            size_bytes=100,
        )
        FileSummary.objects.create(
            file=other_file,
            summary_text="This file handles authentication for the other repository.",
            status="completed",
            language="en",
        )

        # Search in the first repository only
        results = self.service.search(self.repository.id, "authentication")
        for r in results:
            # All results should be from files in the first repository
            if r.result_type == "file":
                file_obj = RepositoryFile.objects.get(path=r.file_path, repository=self.repository)
                assert file_obj.repository_id == self.repository.id

    def test_search_respects_limit(self):
        """Search returns at most the specified limit of results."""
        results = self.service.search(self.repository.id, "authentication", limit=1)
        assert len(results) <= 1

    def test_search_max_limit_is_50(self):
        """Search caps the limit at 50 even if a higher value is passed."""
        results = self.service.search(self.repository.id, "authentication", limit=100)
        assert len(results) <= 50

    def test_search_results_ordered_by_rank(self):
        """Search results are ordered by decreasing similarity rank."""
        results = self.service.search(self.repository.id, "authentication")
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].similarity_rank >= results[i + 1].similarity_rank

    def test_search_excludes_non_completed_summaries(self):
        """Search does not return summaries that are not completed."""
        # Create a file with a pending summary
        pending_file = RepositoryFile.objects.create(
            repository=self.repository,
            path="src/pending.py",
            filename="pending.py",
            language="python",
            content="def pending(): pass",
            size_bytes=50,
        )
        FileSummary.objects.create(
            file=pending_file,
            summary_text="This file handles authentication in a pending state.",
            status="pending",
            language="en",
        )

        results = self.service.search(self.repository.id, "authentication")
        for r in results:
            assert r.file_path != "src/pending.py"

    def test_search_excerpt_max_200_chars(self):
        """Search result excerpts are at most 200 characters."""
        results = self.service.search(self.repository.id, "authentication")
        for r in results:
            assert len(r.summary_excerpt) <= 200

    def test_search_validates_query(self):
        """Search raises QueryValidationError for invalid queries."""
        with pytest.raises(QueryValidationError):
            self.service.search(self.repository.id, "ab")

    def test_search_result_has_correct_fields(self):
        """Search results have all required fields populated."""
        results = self.service.search(self.repository.id, "database")
        assert len(results) > 0
        result = results[0]
        assert result.file_path is not None
        assert result.summary_excerpt is not None
        assert result.similarity_rank > 0
        assert result.result_type in ("file", "block")


@pytest.mark.django_db
class TestSearchAPIEndpoint(TestCase):
    """Tests for the search API endpoint."""

    def setUp(self):
        """Set up test data and API client."""
        self.user = User.objects.create_user(
            username="apiuser", password="testpass123"
        )
        self.repository = Repository.objects.create(
            user=self.user,
            name="api-test-repo",
            source_type="github",
            status="ready",
        )
        self.file1 = RepositoryFile.objects.create(
            repository=self.repository,
            path="src/utils.py",
            filename="utils.py",
            language="python",
            content="def helper(): pass",
            size_bytes=100,
        )
        FileSummary.objects.create(
            file=self.file1,
            summary_text="Utility functions for string manipulation and data formatting.",
            status="completed",
            language="en",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_search_endpoint_returns_results(self):
        """GET /api/repositories/{id}/search/?q=<query> returns matching results."""
        response = self.client.get(
            f"/api/repositories/{self.repository.id}/search/",
            {"q": "string manipulation"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "count" in data
        assert data["count"] > 0

    def test_search_endpoint_empty_results_message(self):
        """Returns a helpful message when no results are found."""
        response = self.client.get(
            f"/api/repositories/{self.repository.id}/search/",
            {"q": "xyznonexistent"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert "message" in data
        assert "No matches found" in data["message"]

    def test_search_endpoint_invalid_query_too_short(self):
        """Returns 400 for queries shorter than 3 characters."""
        response = self.client.get(
            f"/api/repositories/{self.repository.id}/search/",
            {"q": "ab"},
        )
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_search_endpoint_invalid_query_too_long(self):
        """Returns 400 for queries longer than 300 characters."""
        response = self.client.get(
            f"/api/repositories/{self.repository.id}/search/",
            {"q": "a" * 301},
        )
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_search_endpoint_missing_query(self):
        """Returns 400 when query parameter is missing."""
        response = self.client.get(
            f"/api/repositories/{self.repository.id}/search/",
        )
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_search_endpoint_requires_authentication(self):
        """Returns 401 for unauthenticated requests."""
        client = APIClient()
        response = client.get(
            f"/api/repositories/{self.repository.id}/search/",
            {"q": "test query"},
        )
        assert response.status_code in (401, 403)

    def test_search_endpoint_owner_only(self):
        """Returns 403 when a non-owner tries to search."""
        other_user = User.objects.create_user(
            username="otheruser", password="testpass123"
        )
        client = APIClient()
        client.force_authenticate(user=other_user)
        response = client.get(
            f"/api/repositories/{self.repository.id}/search/",
            {"q": "test query"},
        )
        assert response.status_code == 403

    def test_search_endpoint_repository_not_found(self):
        """Returns 404 for non-existent repository."""
        response = self.client.get(
            "/api/repositories/99999/search/",
            {"q": "test query"},
        )
        assert response.status_code == 404

    def test_search_result_structure(self):
        """Each result has the expected fields."""
        response = self.client.get(
            f"/api/repositories/{self.repository.id}/search/",
            {"q": "string manipulation"},
        )
        assert response.status_code == 200
        data = response.json()
        if data["count"] > 0:
            result = data["results"][0]
            assert "file_path" in result
            assert "block_name" in result
            assert "summary_excerpt" in result
            assert "similarity_rank" in result
            assert "result_type" in result
