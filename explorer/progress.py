"""
Progress tracking module for the AI Codebase Explorer.

Provides the ProgressService class for tracking and reporting
summarization job progress, deriving repository status, and
sending notifications on status transitions.
"""

import logging
from dataclasses import dataclass

from django.db.models import Count, Q
from django.utils import timezone

from explorer.models import Repository, SummarizationJob

logger = logging.getLogger(__name__)


@dataclass
class ProgressReport:
    """Report of summarization progress for a repository.

    Attributes:
        total_jobs: Total number of summarization jobs.
        completed: Number of completed jobs.
        pending: Number of pending or in-progress jobs.
        failed: Number of failed or permanently failed jobs.
        status: Derived repository status string.
    """

    total_jobs: int
    completed: int
    pending: int
    failed: int
    status: str


class ProgressService:
    """Service for tracking and reporting summarization job progress.

    Queries the SummarizationJob table to compute progress counts,
    derives repository status based on job states, and handles
    status transitions including notifications.
    """

    def get_progress(self, repository_id: int) -> ProgressReport:
        """Compute progress for a repository's summarization jobs.

        Queries the SummarizationJob table to count completed, pending,
        and failed jobs, then derives the repository status.

        Args:
            repository_id: The ID of the repository to check progress for.

        Returns:
            A ProgressReport with counts and derived status.

        Raises:
            Repository.DoesNotExist: If the repository does not exist.
        """
        repository = Repository.objects.get(id=repository_id)

        # Aggregate job counts by status category
        counts = SummarizationJob.objects.filter(
            repository_id=repository_id
        ).aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status="completed")),
            pending=Count(
                "id", filter=Q(status__in=["pending", "in_progress"])
            ),
            failed=Count(
                "id", filter=Q(status__in=["failed", "permanently_failed"])
            ),
        )

        total = counts["total"] or 0
        completed = counts["completed"] or 0
        pending = counts["pending"] or 0
        failed = counts["failed"] or 0

        # Derive status from job counts
        status = self._derive_status(repository, total, completed, pending, failed)

        return ProgressReport(
            total_jobs=total,
            completed=completed,
            pending=pending,
            failed=failed,
            status=status,
        )

    def update_job_state(self, job_id: int, state: str) -> None:
        """Update a summarization job's status and handle transitions.

        Updates the job status in the database. When a terminal state
        is reached (completed, failed, permanently_failed), checks if
        all jobs for the repository are done and triggers status updates.

        Args:
            job_id: The ID of the SummarizationJob to update.
            state: The new status string for the job.

        Raises:
            SummarizationJob.DoesNotExist: If the job does not exist.
            ValueError: If the state is not a valid job status.
        """
        valid_states = {"pending", "in_progress", "completed", "failed", "permanently_failed"}
        if state not in valid_states:
            raise ValueError(
                f"Invalid job state: '{state}'. Must be one of {valid_states}."
            )

        job = SummarizationJob.objects.select_related("repository").get(id=job_id)
        job.status = state

        if state == "completed":
            job.completed_at = timezone.now()
            job.save(update_fields=["status", "completed_at"])
        else:
            job.save(update_fields=["status"])

        # Check if all jobs are in a terminal state and update repository
        if state in ("completed", "failed", "permanently_failed"):
            self._check_repository_completion(job.repository)

    def _derive_status(
        self,
        repository: Repository,
        total: int,
        completed: int,
        pending: int,
        failed: int,
    ) -> str:
        """Derive the repository status from job counts.

        Status derivation rules:
        - If no jobs exist, return the current repository status
          (could be cloning, parsing, etc.)
        - "ready" if all jobs are completed
        - "failed" if all jobs are failed or permanently_failed
        - "partially_summarized" if at least one completed AND at least
          one failed/permanently_failed with none pending
        - "summarizing" if any jobs are still pending or in_progress

        Args:
            repository: The Repository instance.
            total: Total number of jobs.
            completed: Number of completed jobs.
            pending: Number of pending/in_progress jobs.
            failed: Number of failed/permanently_failed jobs.

        Returns:
            The derived status string.
        """
        if total == 0:
            # No summarization jobs yet — return current repo status
            return repository.status

        if pending > 0:
            return "summarizing"

        if completed == total:
            return "ready"

        if failed == total:
            return "failed"

        if completed > 0 and failed > 0 and pending == 0:
            return "partially_summarized"

        # Fallback — shouldn't normally reach here
        return repository.status

    def _check_repository_completion(self, repository: Repository) -> None:
        """Check if all jobs for a repository are done and update status.

        Called after a job reaches a terminal state. If no pending jobs
        remain, updates the repository status and sends a notification
        if the status transitions to "ready".

        Args:
            repository: The Repository instance to check.
        """
        pending_count = SummarizationJob.objects.filter(
            repository=repository,
            status__in=["pending", "in_progress"],
        ).count()

        if pending_count > 0:
            # Still processing — no status change needed
            return

        # All jobs are in terminal state — derive final status
        progress = self.get_progress(repository.id)
        new_status = progress.status

        old_status = repository.status
        if new_status != old_status:
            repository.status = new_status
            repository.save(update_fields=["status", "updated_at"])

            logger.info(
                "Repository %d status changed: %s -> %s",
                repository.id,
                old_status,
                new_status,
            )

            # Send notification when repository becomes ready
            if new_status == "ready":
                self._send_ready_notification(repository)

    def _send_ready_notification(self, repository: Repository) -> None:
        """Send an in-app notification when a repository is ready.

        Logs the notification event. In a full implementation, this would
        integrate with a notification system (e.g., Django channels,
        push notifications, or an in-app notification model).

        Args:
            repository: The Repository that is now ready.
        """
        logger.info(
            "Notification: Repository '%s' (id=%d) owned by user '%s' "
            "is now ready to browse.",
            repository.name,
            repository.id,
            repository.user.username,
        )
