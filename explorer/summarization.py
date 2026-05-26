"""
AI Summarization module for the AI Codebase Explorer.

Provides the SummarizationService class for generating AI summaries
of repository files and code blocks using OpenAI GPT-4o-mini.
Includes Celery tasks with retry logic and job tracking.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from openai import (
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from explorer.models import (
    BlockSummary,
    CodeBlock,
    FileSummary,
    Repository,
    RepositoryFile,
    SummarizationJob,
)

logger = logging.getLogger(__name__)


class SummarizationError(Exception):
    """Raised when summarization encounters an error."""
    pass


class SummaryValidationError(SummarizationError):
    """Raised when a generated summary fails validation."""
    pass


class SummarizationService:
    """Service for generating AI summaries of files and code blocks.

    Uses OpenAI GPT-4o-mini to generate plain-language summaries
    in the user's preferred language.
    """

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    def summarize_file(self, file: RepositoryFile, language: str) -> FileSummary:
        """Generate an AI summary for a repository file.

        Constructs a prompt requesting the file's purpose, responsibilities,
        and exports/interfaces in the specified language. Validates the response
        is 50-500 words and stores the FileSummary.

        Args:
            file: The RepositoryFile to summarize.
            language: The language code for the summary (e.g., "en", "es").

        Returns:
            The created or updated FileSummary instance.

        Raises:
            SummaryValidationError: If the generated summary fails validation.
            SummarizationError: If the OpenAI API returns an error.
        """
        prompt = self._build_file_prompt(file, language)
        summary_text = self._call_openai(prompt)

        # Validate word count (50-500 words)
        word_count = len(summary_text.split())
        if word_count < 50 or word_count > 500:
            raise SummaryValidationError(
                f"File summary has {word_count} words, expected 50-500."
            )

        # Store or update the FileSummary
        file_summary, created = FileSummary.objects.update_or_create(
            file=file,
            defaults={
                "summary_text": summary_text,
                "status": "completed",
                "language": language,
                "generated_at": timezone.now(),
            },
        )

        return file_summary

    def summarize_block(
        self, block: CodeBlock, file_context: str, language: str
    ) -> BlockSummary:
        """Generate an AI summary for a code block.

        Constructs a prompt requesting the block's purpose, parameters,
        return value, side effects, and references in the specified language.
        Validates the response is at most 500 characters and stores the BlockSummary.

        Args:
            block: The CodeBlock to summarize.
            file_context: Brief context about the file containing this block.
            language: The language code for the summary (e.g., "en", "es").

        Returns:
            The created or updated BlockSummary instance.

        Raises:
            SummaryValidationError: If the generated summary fails validation.
            SummarizationError: If the OpenAI API returns an error.
        """
        prompt = self._build_block_prompt(block, file_context, language)
        summary_text = self._call_openai(prompt)

        # Validate character count (max 500 chars)
        if len(summary_text) > 500:
            # Truncate to 500 chars at a word boundary
            summary_text = summary_text[:497].rsplit(" ", 1)[0] + "..."

        # Store or update the BlockSummary
        block_summary, created = BlockSummary.objects.update_or_create(
            block=block,
            defaults={
                "summary_text": summary_text,
                "status": "completed",
                "language": language,
                "generated_at": timezone.now(),
            },
        )

        return block_summary

    def retry_failed(self, repository_id: int) -> int:
        """Re-enqueue failed summarization jobs for a repository.

        Re-enqueues jobs that are in 'failed' status (not 'permanently_failed'
        and not 'completed'). Resets their status to 'pending' and dispatches
        new Celery tasks.

        Args:
            repository_id: The ID of the repository to retry failed jobs for.

        Returns:
            The count of jobs that were re-enqueued.
        """
        failed_jobs = SummarizationJob.objects.filter(
            repository_id=repository_id,
            status="failed",
        )

        count = 0
        for job in failed_jobs:
            job.status = "pending"
            job.save(update_fields=["status"])

            # Get the language from the repository's user preference
            language = job.repository.user.language_preference

            if job.job_type == "file" and job.file_id:
                summarize_file_task.delay(job.file_id, language)
            elif job.job_type == "block" and job.block_id:
                summarize_block_task.delay(job.block_id, language)

            count += 1

        return count

    def _build_file_prompt(self, file: RepositoryFile, language: str) -> str:
        """Build the prompt for file summarization.

        Args:
            file: The RepositoryFile to summarize.
            language: The language code for the summary.

        Returns:
            The constructed prompt string.
        """
        language_name = self._get_language_name(language)

        # Truncate content if too long (keep first 8000 chars for context)
        content = file.content
        if len(content) > 8000:
            content = content[:8000] + "\n\n... [truncated]"

        return (
            f"You are a code documentation expert. Analyze the following source code file "
            f"and provide a summary in {language_name}.\n\n"
            f"File: {file.path}\n"
            f"Language: {file.language}\n\n"
            f"Source code:\n```\n{content}\n```\n\n"
            f"Please provide a summary that includes:\n"
            f"1. **Purpose**: What problem this file solves or what role it plays in the project.\n"
            f"2. **Responsibilities**: All public functions, classes, or handlers it defines.\n"
            f"3. **Exports/Interfaces**: All symbols exported or made available to other modules.\n\n"
            f"Requirements:\n"
            f"- Write the summary in {language_name}.\n"
            f"- The summary must be between 50 and 500 words.\n"
            f"- Use clear, plain language that a developer unfamiliar with the codebase can understand.\n"
            f"- Do not include code snippets in the summary."
        )

    def _build_block_prompt(
        self, block: CodeBlock, file_context: str, language: str
    ) -> str:
        """Build the prompt for code block summarization.

        Args:
            block: The CodeBlock to summarize.
            file_context: Brief context about the file containing this block.
            language: The language code for the summary.

        Returns:
            The constructed prompt string.
        """
        language_name = self._get_language_name(language)

        return (
            f"You are a code documentation expert. Analyze the following code block "
            f"and provide a concise summary in {language_name}.\n\n"
            f"File context: {file_context}\n"
            f"Block type: {block.kind}\n"
            f"Block name: {block.name}\n\n"
            f"Source code:\n```\n{block.content}\n```\n\n"
            f"Please provide a summary that includes:\n"
            f"1. **Purpose**: What this {block.kind} does.\n"
            f"2. **Parameters/Inputs**: What arguments or inputs it accepts.\n"
            f"3. **Return value/Output**: What it returns or produces.\n"
            f"4. **Side effects**: Any side effects (database writes, API calls, etc.).\n"
            f"5. **References**: Other code blocks it calls or is called by.\n\n"
            f"Requirements:\n"
            f"- Write the summary in {language_name}.\n"
            f"- The summary must be at most 500 characters.\n"
            f"- Be concise and informative."
        )

    def _call_openai(self, prompt: str) -> str:
        """Call the OpenAI API to generate a summary.

        Args:
            prompt: The prompt to send to the API.

        Returns:
            The generated summary text.

        Raises:
            RateLimitError: If the API rate limit is exceeded.
            APITimeoutError: If the API request times out.
            SummarizationError: For other API errors.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful code documentation assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )
            return response.choices[0].message.content.strip()
        except (RateLimitError, APITimeoutError):
            # Re-raise these for retry handling in Celery tasks
            raise
        except Exception as e:
            raise SummarizationError(f"OpenAI API error: {str(e)}")

    @staticmethod
    def _get_language_name(language_code: str) -> str:
        """Convert a language code to a human-readable language name.

        Args:
            language_code: The ISO language code (e.g., "en", "es").

        Returns:
            The human-readable language name.
        """
        language_map = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "pt": "Portuguese",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese (Simplified)",
        }
        return language_map.get(language_code, "English")


@shared_task(bind=True, max_retries=3)
def summarize_file_task(self, file_id: int, language: str) -> None:
    """Celery task to summarize a single file.

    Creates/updates a SummarizationJob record to track progress.
    Implements exponential backoff:
    - Rate limit errors: 30s base (30, 60, 120)
    - Timeout errors: 15s base (15, 30, 60)
    After 3 retries exhausted, marks as permanently_failed.

    Args:
        file_id: The ID of the RepositoryFile to summarize.
        language: The language code for the summary.
    """
    try:
        file = RepositoryFile.objects.get(id=file_id)
    except RepositoryFile.DoesNotExist:
        logger.error("RepositoryFile %d not found for summarization.", file_id)
        return

    # Get or create the SummarizationJob
    job = SummarizationJob.objects.filter(
        file=file,
        job_type="file",
        repository=file.repository,
    ).first()

    if not job:
        job = SummarizationJob.objects.create(
            repository=file.repository,
            file=file,
            job_type="file",
            status="in_progress",
        )
    else:
        job.status = "in_progress"
        job.save(update_fields=["status"])

    try:
        service = SummarizationService()
        service.summarize_file(file, language)

        # Mark job as completed
        job.status = "completed"
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "completed_at"])

        logger.info("Successfully summarized file %s (id=%d)", file.path, file_id)

    except RateLimitError as exc:
        # Exponential backoff with 30s base
        job.retry_count += 1
        job.error_message = f"Rate limit error: {str(exc)}"
        job.save(update_fields=["retry_count", "error_message"])

        if self.request.retries >= self.max_retries:
            _mark_permanently_failed(job, file_summary=True, file=file)
            return

        countdown = (2 ** self.request.retries) * 30
        raise self.retry(exc=exc, countdown=countdown)

    except APITimeoutError as exc:
        # Exponential backoff with 15s base
        job.retry_count += 1
        job.error_message = f"Timeout error: {str(exc)}"
        job.save(update_fields=["retry_count", "error_message"])

        if self.request.retries >= self.max_retries:
            _mark_permanently_failed(job, file_summary=True, file=file)
            return

        countdown = (2 ** self.request.retries) * 15
        raise self.retry(exc=exc, countdown=countdown)

    except (SummarizationError, SummaryValidationError) as exc:
        # Non-retryable errors — mark as failed
        job.retry_count += 1
        job.status = "failed"
        job.error_message = str(exc)
        job.save(update_fields=["retry_count", "status", "error_message"])

        # Mark the file summary as failed
        FileSummary.objects.update_or_create(
            file=file,
            defaults={
                "summary_text": "",
                "status": "failed",
                "language": language,
            },
        )
        logger.warning("Summarization failed for file %s: %s", file.path, str(exc))

    except Exception as exc:
        # Unexpected errors
        job.retry_count += 1
        job.error_message = f"Unexpected error: {str(exc)}"
        job.save(update_fields=["retry_count", "error_message"])

        if self.request.retries >= self.max_retries:
            _mark_permanently_failed(job, file_summary=True, file=file)
            return

        countdown = (2 ** self.request.retries) * 15
        try:
            raise self.retry(exc=exc, countdown=countdown)
        except self.MaxRetriesExceededError:
            _mark_permanently_failed(job, file_summary=True, file=file)


@shared_task(bind=True, max_retries=3)
def summarize_block_task(self, block_id: int, language: str) -> None:
    """Celery task to summarize a single code block.

    Creates/updates a SummarizationJob record to track progress.
    Implements exponential backoff:
    - Rate limit errors: 30s base (30, 60, 120)
    - Timeout errors: 15s base (15, 30, 60)
    After 3 retries exhausted, marks as permanently_failed.

    Args:
        block_id: The ID of the CodeBlock to summarize.
        language: The language code for the summary.
    """
    try:
        block = CodeBlock.objects.select_related("file").get(id=block_id)
    except CodeBlock.DoesNotExist:
        logger.error("CodeBlock %d not found for summarization.", block_id)
        return

    # Get or create the SummarizationJob
    job = SummarizationJob.objects.filter(
        block=block,
        job_type="block",
        repository=block.file.repository,
    ).first()

    if not job:
        job = SummarizationJob.objects.create(
            repository=block.file.repository,
            block=block,
            file=block.file,
            job_type="block",
            status="in_progress",
        )
    else:
        job.status = "in_progress"
        job.save(update_fields=["status"])

    # Build file context for the block prompt
    file_context = f"{block.file.path} ({block.file.language})"

    try:
        service = SummarizationService()
        service.summarize_block(block, file_context, language)

        # Mark job as completed
        job.status = "completed"
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "completed_at"])

        logger.info(
            "Successfully summarized block %s in %s (id=%d)",
            block.name,
            block.file.path,
            block_id,
        )

    except RateLimitError as exc:
        # Exponential backoff with 30s base
        job.retry_count += 1
        job.error_message = f"Rate limit error: {str(exc)}"
        job.save(update_fields=["retry_count", "error_message"])

        if self.request.retries >= self.max_retries:
            _mark_permanently_failed(job, file_summary=False, block=block)
            return

        countdown = (2 ** self.request.retries) * 30
        raise self.retry(exc=exc, countdown=countdown)

    except APITimeoutError as exc:
        # Exponential backoff with 15s base
        job.retry_count += 1
        job.error_message = f"Timeout error: {str(exc)}"
        job.save(update_fields=["retry_count", "error_message"])

        if self.request.retries >= self.max_retries:
            _mark_permanently_failed(job, file_summary=False, block=block)
            return

        countdown = (2 ** self.request.retries) * 15
        raise self.retry(exc=exc, countdown=countdown)

    except (SummarizationError, SummaryValidationError) as exc:
        # Non-retryable errors — mark as failed
        job.retry_count += 1
        job.status = "failed"
        job.error_message = str(exc)
        job.save(update_fields=["retry_count", "status", "error_message"])

        # Mark the block summary as failed
        BlockSummary.objects.update_or_create(
            block=block,
            defaults={
                "summary_text": "",
                "status": "failed",
                "language": language,
            },
        )
        logger.warning(
            "Summarization failed for block %s: %s", block.name, str(exc)
        )

    except Exception as exc:
        # Unexpected errors
        job.retry_count += 1
        job.error_message = f"Unexpected error: {str(exc)}"
        job.save(update_fields=["retry_count", "error_message"])

        if self.request.retries >= self.max_retries:
            _mark_permanently_failed(job, file_summary=False, block=block)
            return

        countdown = (2 ** self.request.retries) * 15
        try:
            raise self.retry(exc=exc, countdown=countdown)
        except self.MaxRetriesExceededError:
            _mark_permanently_failed(job, file_summary=False, block=block)


def _mark_permanently_failed(job, file_summary=True, file=None, block=None):
    """Mark a summarization job and its associated summary as permanently failed.

    Args:
        job: The SummarizationJob instance.
        file_summary: If True, marks a FileSummary; otherwise marks a BlockSummary.
        file: The RepositoryFile (for file summaries).
        block: The CodeBlock (for block summaries).
    """
    job.status = "permanently_failed"
    job.save(update_fields=["status"])

    if file_summary and file:
        FileSummary.objects.update_or_create(
            file=file,
            defaults={
                "summary_text": "",
                "status": "permanently_failed",
                "language": "",
            },
        )
        logger.warning(
            "File %s permanently failed summarization after 3 retries.", file.path
        )
    elif not file_summary and block:
        BlockSummary.objects.update_or_create(
            block=block,
            defaults={
                "summary_text": "",
                "status": "permanently_failed",
                "language": "",
            },
        )
        logger.warning(
            "Block %s permanently failed summarization after 3 retries.", block.name
        )


def enqueue_summarization_jobs(repository_id: int, language: str) -> int:
    """Enqueue summarization jobs for all summarizable files and their code blocks.

    Called after ingestion and parsing completes. Creates SummarizationJob records
    and dispatches Celery tasks for each summarizable file and its code blocks.

    Args:
        repository_id: The ID of the repository to enqueue jobs for.
        language: The language code for summaries.

    Returns:
        The total number of jobs enqueued.
    """
    try:
        repository = Repository.objects.get(id=repository_id)
    except Repository.DoesNotExist:
        logger.error("Repository %d not found for summarization enqueueing.", repository_id)
        return 0

    # Update repository status to summarizing
    repository.status = "summarizing"
    repository.save(update_fields=["status"])

    jobs_enqueued = 0

    # Get all summarizable files
    summarizable_files = RepositoryFile.objects.filter(
        repository=repository,
        is_summarizable=True,
    )

    for file in summarizable_files:
        # Create a SummarizationJob for the file
        job, created = SummarizationJob.objects.get_or_create(
            repository=repository,
            file=file,
            job_type="file",
            defaults={"status": "pending"},
        )
        if created:
            summarize_file_task.delay(file.id, language)
            jobs_enqueued += 1

        # Create SummarizationJobs for each code block in the file
        code_blocks = CodeBlock.objects.filter(file=file)
        for block in code_blocks:
            block_job, block_created = SummarizationJob.objects.get_or_create(
                repository=repository,
                block=block,
                job_type="block",
                defaults={"status": "pending", "file": file},
            )
            if block_created:
                summarize_block_task.delay(block.id, language)
                jobs_enqueued += 1

    logger.info(
        "Enqueued %d summarization jobs for repository %d.",
        jobs_enqueued,
        repository_id,
    )

    return jobs_enqueued
