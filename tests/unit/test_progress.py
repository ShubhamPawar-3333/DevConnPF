"""
Unit tests for the progress tracking module.

Tests the ProgressService class including status derivation logic,
job state updates, repository status transitions, and the API endpoint.
"""

import pytest
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.test import force_authenticate

from explorer.models import (
    Repository,
    RepositoryFile,
    SummarizationJob,
    User,
)
from explorer.progress import ProgressReport, ProgressService
from explorer.views import repository_progress_view


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
        status="summarizing",
    )


@pytest.fixture
def repo_file(repository):
    """Create a test repository file."""
    return RepositoryFile.objects.create(
        repository=repository,
        path="src/main.py",
        filename="main.py",
        language="python",
        content="print('hello')",
        size_bytes=14,
        is_summarizable=True,
    )


@pytest.fixture
def progress_service():
    """Create a ProgressService instance."""
    return ProgressService()


@pytest.fixture
def request_factory():
    """Create a Django request factory."""
    return RequestFactory()


class TestProgressServiceGetProgress:
    """Tests for ProgressService.get_progress()."""

    def test_no_jobs_returns_current_repo_status(self, progress_service, repository):
        """When no jobs exist, return the current repository status."""
        progress = progress_service.get_progress(repository.id)

        assert progress.total_jobs == 0
        assert progress.completed == 0
        assert progress.pending == 0
        assert progress.failed == 0
        assert progress.status == "summarizing"

    def test_all_completed_returns_ready(self, progress_service, repository, repo_file):
        """When all jobs are completed, status should be 'ready'."""
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="completed",
        )
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="block",
            status="completed",
        )

        progress = progress_service.get_progress(repository.id)

        assert progress.total_jobs == 2
        assert progress.completed == 2
        assert progress.pending == 0
        assert progress.failed == 0
        assert progress.status == "ready"

    def test_all_failed_returns_failed(self, progress_service, repository, repo_file):
        """When all jobs are failed, status should be 'failed'."""
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="failed",
        )
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="block",
            status="permanently_failed",
        )

        progress = progress_service.get_progress(repository.id)

        assert progress.total_jobs == 2
        assert progress.completed == 0
        assert progress.pending == 0
        assert progress.failed == 2
        assert progress.status == "failed"

    def test_mixed_completed_and_failed_returns_partially_summarized(
        self, progress_service, repository, repo_file
    ):
        """When some completed and some failed with none pending, status is 'partially_summarized'."""
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="completed",
        )
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="block",
            status="failed",
        )

        progress = progress_service.get_progress(repository.id)

        assert progress.total_jobs == 2
        assert progress.completed == 1
        assert progress.pending == 0
        assert progress.failed == 1
        assert progress.status == "partially_summarized"

    def test_pending_jobs_returns_summarizing(
        self, progress_service, repository, repo_file
    ):
        """When any jobs are pending or in_progress, status is 'summarizing'."""
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="completed",
        )
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="block",
            status="pending",
        )

        progress = progress_service.get_progress(repository.id)

        assert progress.total_jobs == 2
        assert progress.completed == 1
        assert progress.pending == 1
        assert progress.failed == 0
        assert progress.status == "summarizing"

    def test_in_progress_jobs_returns_summarizing(
        self, progress_service, repository, repo_file
    ):
        """In-progress jobs count as pending and result in 'summarizing' status."""
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="in_progress",
        )

        progress = progress_service.get_progress(repository.id)

        assert progress.total_jobs == 1
        assert progress.pending == 1
        assert progress.status == "summarizing"

    def test_counts_sum_to_total(self, progress_service, repository, repo_file):
        """completed + pending + failed should always equal total."""
        SummarizationJob.objects.create(
            repository=repository, file=repo_file, job_type="file", status="completed"
        )
        SummarizationJob.objects.create(
            repository=repository, file=repo_file, job_type="block", status="pending"
        )
        SummarizationJob.objects.create(
            repository=repository, file=repo_file, job_type="block", status="failed"
        )
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="block",
            status="permanently_failed",
        )

        progress = progress_service.get_progress(repository.id)

        assert progress.completed + progress.pending + progress.failed == progress.total_jobs

    def test_nonexistent_repository_raises(self, progress_service, db):
        """Querying a non-existent repository raises DoesNotExist."""
        with pytest.raises(Repository.DoesNotExist):
            progress_service.get_progress(99999)


class TestProgressServiceUpdateJobState:
    """Tests for ProgressService.update_job_state()."""

    def test_update_to_completed(self, progress_service, repository, repo_file):
        """Updating a job to 'completed' sets completed_at timestamp."""
        job = SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="in_progress",
        )

        progress_service.update_job_state(job.id, "completed")

        job.refresh_from_db()
        assert job.status == "completed"
        assert job.completed_at is not None

    def test_update_to_failed(self, progress_service, repository, repo_file):
        """Updating a job to 'failed' does not set completed_at."""
        job = SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="in_progress",
        )

        progress_service.update_job_state(job.id, "failed")

        job.refresh_from_db()
        assert job.status == "failed"
        assert job.completed_at is None

    def test_invalid_state_raises_value_error(self, progress_service, repository, repo_file):
        """Passing an invalid state raises ValueError."""
        job = SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="pending",
        )

        with pytest.raises(ValueError, match="Invalid job state"):
            progress_service.update_job_state(job.id, "invalid_state")

    def test_nonexistent_job_raises(self, progress_service, db):
        """Updating a non-existent job raises DoesNotExist."""
        with pytest.raises(SummarizationJob.DoesNotExist):
            progress_service.update_job_state(99999, "completed")

    def test_repository_status_updated_when_all_complete(
        self, progress_service, repository, repo_file
    ):
        """Repository status updates to 'ready' when all jobs complete."""
        job1 = SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="completed",
        )
        job2 = SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="block",
            status="in_progress",
        )

        progress_service.update_job_state(job2.id, "completed")

        repository.refresh_from_db()
        assert repository.status == "ready"

    def test_repository_status_partially_summarized(
        self, progress_service, repository, repo_file
    ):
        """Repository status updates to 'partially_summarized' on mixed results."""
        job1 = SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="completed",
        )
        job2 = SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="block",
            status="in_progress",
        )

        progress_service.update_job_state(job2.id, "permanently_failed")

        repository.refresh_from_db()
        assert repository.status == "partially_summarized"

    def test_repository_status_not_updated_while_pending(
        self, progress_service, repository, repo_file
    ):
        """Repository status stays unchanged while jobs are still pending."""
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="pending",
        )
        job2 = SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="block",
            status="in_progress",
        )

        progress_service.update_job_state(job2.id, "completed")

        repository.refresh_from_db()
        assert repository.status == "summarizing"  # unchanged


class TestRepositoryProgressAPI:
    """Tests for the GET /api/repositories/{id}/progress/ endpoint."""

    def test_authenticated_owner_gets_progress(
        self, request_factory, user, repository, repo_file
    ):
        """Authenticated owner can access their repository's progress."""
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="completed",
        )

        request = request_factory.get(f"/api/repositories/{repository.id}/progress/")
        force_authenticate(request, user=user)

        response = repository_progress_view(request, repository_id=repository.id)

        assert response.status_code == 200
        assert response.data["total"] == 1
        assert response.data["completed"] == 1
        assert response.data["pending"] == 0
        assert response.data["failed"] == 0
        assert response.data["status"] == "ready"

    def test_non_owner_gets_403(
        self, request_factory, other_user, repository
    ):
        """Non-owner gets 403 Forbidden."""
        request = request_factory.get(f"/api/repositories/{repository.id}/progress/")
        force_authenticate(request, user=other_user)

        response = repository_progress_view(request, repository_id=repository.id)

        assert response.status_code == 403

    def test_nonexistent_repository_gets_404(self, request_factory, user):
        """Non-existent repository returns 404."""
        request = request_factory.get("/api/repositories/99999/progress/")
        force_authenticate(request, user=user)

        response = repository_progress_view(request, repository_id=99999)

        assert response.status_code == 404

    def test_unauthenticated_gets_403(self, request_factory, repository):
        """Unauthenticated request gets 403."""
        request = request_factory.get(f"/api/repositories/{repository.id}/progress/")

        response = repository_progress_view(request, repository_id=repository.id)

        assert response.status_code == 403
