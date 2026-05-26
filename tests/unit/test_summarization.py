"""
Unit tests for the summarization service and Celery tasks.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase, override_settings
from django.utils import timezone

from explorer.models import (
    BlockSummary,
    CodeBlock,
    FileSummary,
    Repository,
    RepositoryFile,
    SummarizationJob,
    User,
)
from explorer.summarization import (
    SummarizationService,
    SummaryValidationError,
    enqueue_summarization_jobs,
    summarize_block_task,
    summarize_file_task,
)


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        password="testpass123",
        language_preference="en",
    )


@pytest.fixture
def repository(user):
    """Create a test repository."""
    return Repository.objects.create(
        user=user,
        name="test-repo",
        source_type="github",
        github_full_name="owner/test-repo",
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
        content="def hello():\n    print('hello world')\n",
        size_bytes=40,
        is_summarizable=True,
    )


@pytest.fixture
def code_block(repo_file):
    """Create a test code block."""
    return CodeBlock.objects.create(
        file=repo_file,
        name="hello",
        kind="function",
        start_line=1,
        end_line=2,
        content="def hello():\n    print('hello world')\n",
        parent_block_name=None,
    )


@pytest.mark.django_db
class TestSummarizationServicePrompts:
    """Test prompt construction for the summarization service."""

    @patch("explorer.summarization.OpenAI")
    def test_file_prompt_includes_language(self, mock_openai_cls, repo_file):
        """Test that file prompt includes the correct language."""
        service = SummarizationService()
        prompt = service._build_file_prompt(repo_file, "es")
        assert "Spanish" in prompt
        assert "src/main.py" in prompt
        assert "python" in prompt

    @patch("explorer.summarization.OpenAI")
    def test_file_prompt_includes_required_sections(self, mock_openai_cls, repo_file):
        """Test that file prompt requests purpose, responsibilities, exports."""
        service = SummarizationService()
        prompt = service._build_file_prompt(repo_file, "en")
        assert "Purpose" in prompt
        assert "Responsibilities" in prompt
        assert "Exports/Interfaces" in prompt

    @patch("explorer.summarization.OpenAI")
    def test_block_prompt_includes_language(self, mock_openai_cls, code_block):
        """Test that block prompt includes the correct language."""
        service = SummarizationService()
        prompt = service._build_block_prompt(code_block, "src/main.py (python)", "fr")
        assert "French" in prompt
        assert "hello" in prompt
        assert "function" in prompt

    @patch("explorer.summarization.OpenAI")
    def test_block_prompt_includes_required_sections(self, mock_openai_cls, code_block):
        """Test that block prompt requests purpose, params, return, side effects, refs."""
        service = SummarizationService()
        prompt = service._build_block_prompt(code_block, "src/main.py", "en")
        assert "Purpose" in prompt
        assert "Parameters" in prompt
        assert "Return value" in prompt
        assert "Side effects" in prompt
        assert "References" in prompt

    @patch("explorer.summarization.OpenAI")
    def test_file_prompt_truncates_long_content(self, mock_openai_cls, repo_file):
        """Test that file prompt truncates content longer than 8000 chars."""
        repo_file.content = "x" * 10000
        service = SummarizationService()
        prompt = service._build_file_prompt(repo_file, "en")
        assert "[truncated]" in prompt


@pytest.mark.django_db
class TestSummarizationServiceValidation:
    """Test summary validation logic."""

    @patch("explorer.summarization.OpenAI")
    def test_file_summary_rejects_too_short(self, mock_openai_cls, repo_file):
        """Test that file summary rejects text with fewer than 50 words."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Too short summary."
        mock_client.chat.completions.create.return_value = mock_response

        service = SummarizationService()
        service.client = mock_client

        with pytest.raises(SummaryValidationError, match="words"):
            service.summarize_file(repo_file, "en")

    @patch("explorer.summarization.OpenAI")
    def test_file_summary_rejects_too_long(self, mock_openai_cls, repo_file):
        """Test that file summary rejects text with more than 500 words."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        # Generate 501 words
        mock_response.choices[0].message.content = " ".join(["word"] * 501)
        mock_client.chat.completions.create.return_value = mock_response

        service = SummarizationService()
        service.client = mock_client

        with pytest.raises(SummaryValidationError, match="words"):
            service.summarize_file(repo_file, "en")

    @patch("explorer.summarization.OpenAI")
    def test_file_summary_accepts_valid_length(self, mock_openai_cls, repo_file):
        """Test that file summary accepts text with 50-500 words."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        # Generate exactly 100 words
        mock_response.choices[0].message.content = " ".join(["word"] * 100)
        mock_client.chat.completions.create.return_value = mock_response

        service = SummarizationService()
        service.client = mock_client

        result = service.summarize_file(repo_file, "en")
        assert result.status == "completed"
        assert result.language == "en"

    @patch("explorer.summarization.OpenAI")
    def test_block_summary_truncates_over_500_chars(self, mock_openai_cls, code_block):
        """Test that block summary truncates text over 500 characters."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        # Generate text over 500 chars
        mock_response.choices[0].message.content = "a " * 300  # 600 chars
        mock_client.chat.completions.create.return_value = mock_response

        service = SummarizationService()
        service.client = mock_client

        result = service.summarize_block(code_block, "src/main.py", "en")
        assert len(result.summary_text) <= 500
        assert result.status == "completed"

    @patch("explorer.summarization.OpenAI")
    def test_block_summary_accepts_valid_length(self, mock_openai_cls, code_block):
        """Test that block summary accepts text at most 500 characters."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "A short block summary."
        mock_client.chat.completions.create.return_value = mock_response

        service = SummarizationService()
        service.client = mock_client

        result = service.summarize_block(code_block, "src/main.py", "en")
        assert result.summary_text == "A short block summary."
        assert result.status == "completed"


@pytest.mark.django_db
class TestSummarizationJobTracking:
    """Test SummarizationJob creation and tracking."""

    def test_enqueue_creates_jobs_for_summarizable_files(
        self, repository, repo_file, code_block
    ):
        """Test that enqueue creates jobs for files and blocks."""
        with patch("explorer.summarization.summarize_file_task") as mock_file_task, \
             patch("explorer.summarization.summarize_block_task") as mock_block_task:
            mock_file_task.delay = MagicMock()
            mock_block_task.delay = MagicMock()

            count = enqueue_summarization_jobs(repository.id, "en")

            assert count == 2  # 1 file + 1 block
            assert SummarizationJob.objects.filter(
                repository=repository, job_type="file"
            ).count() == 1
            assert SummarizationJob.objects.filter(
                repository=repository, job_type="block"
            ).count() == 1

    def test_enqueue_skips_non_summarizable_files(self, repository):
        """Test that enqueue skips files marked as non-summarizable."""
        RepositoryFile.objects.create(
            repository=repository,
            path="image.png",
            filename="image.png",
            language="unknown",
            content="binary data",
            size_bytes=1000,
            is_summarizable=False,
        )

        with patch("explorer.summarization.summarize_file_task") as mock_file_task:
            mock_file_task.delay = MagicMock()
            count = enqueue_summarization_jobs(repository.id, "en")

            assert count == 0
            mock_file_task.delay.assert_not_called()

    def test_enqueue_updates_repository_status(self, repository, repo_file):
        """Test that enqueue sets repository status to 'summarizing'."""
        repository.status = "parsing"
        repository.save()

        with patch("explorer.summarization.summarize_file_task") as mock_file_task:
            mock_file_task.delay = MagicMock()
            enqueue_summarization_jobs(repository.id, "en")

        repository.refresh_from_db()
        assert repository.status == "summarizing"


@pytest.mark.django_db
class TestRetryFailed:
    """Test retry_failed functionality."""

    @patch("explorer.summarization.OpenAI")
    def test_retry_failed_re_enqueues_failed_jobs(
        self, mock_openai_cls, repository, repo_file
    ):
        """Test that retry_failed re-enqueues failed jobs."""
        # Create a failed job
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="failed",
            retry_count=1,
        )

        with patch("explorer.summarization.summarize_file_task") as mock_task:
            mock_task.delay = MagicMock()
            service = SummarizationService()
            count = service.retry_failed(repository.id)

            assert count == 1
            mock_task.delay.assert_called_once_with(repo_file.id, "en")

    @patch("explorer.summarization.OpenAI")
    def test_retry_failed_skips_permanently_failed(
        self, mock_openai_cls, repository, repo_file
    ):
        """Test that retry_failed skips permanently_failed jobs."""
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="permanently_failed",
            retry_count=3,
        )

        with patch("explorer.summarization.summarize_file_task") as mock_task:
            mock_task.delay = MagicMock()
            service = SummarizationService()
            count = service.retry_failed(repository.id)

            assert count == 0
            mock_task.delay.assert_not_called()

    @patch("explorer.summarization.OpenAI")
    def test_retry_failed_skips_completed_jobs(
        self, mock_openai_cls, repository, repo_file
    ):
        """Test that retry_failed skips completed jobs."""
        SummarizationJob.objects.create(
            repository=repository,
            file=repo_file,
            job_type="file",
            status="completed",
            retry_count=0,
        )

        with patch("explorer.summarization.summarize_file_task") as mock_task:
            mock_task.delay = MagicMock()
            service = SummarizationService()
            count = service.retry_failed(repository.id)

            assert count == 0
            mock_task.delay.assert_not_called()


@pytest.mark.django_db
class TestLanguageMapping:
    """Test language code to name mapping."""

    @patch("explorer.summarization.OpenAI")
    def test_all_supported_languages(self, mock_openai_cls):
        """Test that all supported language codes map to names."""
        service = SummarizationService()
        assert service._get_language_name("en") == "English"
        assert service._get_language_name("es") == "Spanish"
        assert service._get_language_name("fr") == "French"
        assert service._get_language_name("de") == "German"
        assert service._get_language_name("pt") == "Portuguese"
        assert service._get_language_name("ja") == "Japanese"
        assert service._get_language_name("ko") == "Korean"
        assert service._get_language_name("zh") == "Chinese (Simplified)"

    @patch("explorer.summarization.OpenAI")
    def test_unknown_language_defaults_to_english(self, mock_openai_cls):
        """Test that unknown language codes default to English."""
        service = SummarizationService()
        assert service._get_language_name("xx") == "English"
