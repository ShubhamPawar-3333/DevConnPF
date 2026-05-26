import os
import secrets

from django.contrib.auth.models import AbstractUser
from django.db import models

# Conditionally import PostgreSQL-specific features
if os.environ.get("DATABASE_ENGINE") != "sqlite3" and "sqlite3" not in os.environ.get("DATABASE_URL", ""):
    try:
        from django.contrib.postgres.indexes import GinIndex
        from django.contrib.postgres.search import SearchVectorField
        USE_POSTGRES = True
    except ImportError:
        USE_POSTGRES = False
else:
    USE_POSTGRES = False

# Fallback for SQLite: use a nullable TextField instead of SearchVectorField
if not USE_POSTGRES:
    SearchVectorField = lambda **kwargs: models.TextField(null=True, blank=True)  # noqa: E731


class User(AbstractUser):
    """Custom user model with language preference and encrypted GitHub token."""

    LANGUAGE_CHOICES = [
        ("en", "English"),
        ("es", "Spanish"),
        ("fr", "French"),
        ("de", "German"),
        ("pt", "Portuguese"),
        ("ja", "Japanese"),
        ("ko", "Korean"),
        ("zh", "Chinese (Simplified)"),
    ]

    language_preference = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default="en",
    )
    github_token_encrypted = models.BinaryField(null=True, blank=True)

    class Meta:
        db_table = "explorer_user"

    def __str__(self):
        return self.username


class Repository(models.Model):
    """A repository ingested into the Explorer for analysis."""

    SOURCE_TYPE_CHOICES = [
        ("github", "GitHub"),
        ("zip", "ZIP Upload"),
    ]

    STATUS_CHOICES = [
        ("cloning", "Cloning"),
        ("extracting", "Extracting"),
        ("parsing", "Parsing"),
        ("summarizing", "Summarizing"),
        ("ready", "Ready"),
        ("partially_summarized", "Partially Summarized"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="repositories",
    )
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES)
    github_full_name = models.CharField(max_length=255, null=True, blank=True)
    branch = models.CharField(max_length=100, null=True, blank=True)
    commit_sha = models.CharField(max_length=40, null=True, blank=True)
    original_filename = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="cloning")
    file_count = models.IntegerField(default=0)
    total_size_bytes = models.BigIntegerField(default=0)
    ingested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "explorer_repository"
        ordering = ["-ingested_at"]

    def __str__(self):
        return f"{self.name} ({self.source_type})"


class RepositoryFile(models.Model):
    """A single file within an ingested repository."""

    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="files",
    )
    path = models.CharField(max_length=1000)
    filename = models.CharField(max_length=255)
    language = models.CharField(max_length=50, default="unknown")
    content = models.TextField()
    size_bytes = models.IntegerField()
    is_summarizable = models.BooleanField(default=True)

    class Meta:
        db_table = "explorer_repositoryfile"
        constraints = [
            models.UniqueConstraint(
                fields=["repository", "path"],
                name="unique_repository_file_path",
            ),
        ]

    def __str__(self):
        return self.path


class FileSummary(models.Model):
    """AI-generated summary for a repository file."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("permanently_failed", "Permanently Failed"),
    ]

    file = models.OneToOneField(
        RepositoryFile,
        on_delete=models.CASCADE,
        related_name="summary",
    )
    summary_text = models.TextField()
    summary_vector = SearchVectorField(null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    retry_count = models.IntegerField(default=0)
    language = models.CharField(max_length=10, default="en")
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "explorer_filesummary"
        indexes = []  # GinIndex only used with PostgreSQL

    def __str__(self):
        return f"Summary for {self.file.path}"


class CodeBlock(models.Model):
    """A discrete code block (function, class, method) within a file."""

    KIND_CHOICES = [
        ("function", "Function"),
        ("class", "Class"),
        ("method", "Method"),
        ("module_construct", "Module Construct"),
    ]

    file = models.ForeignKey(
        RepositoryFile,
        on_delete=models.CASCADE,
        related_name="code_blocks",
    )
    name = models.CharField(max_length=255)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    start_line = models.IntegerField()
    end_line = models.IntegerField()
    content = models.TextField()
    parent_block_name = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "explorer_codeblock"

    def __str__(self):
        return f"{self.kind}: {self.name}"


class BlockSummary(models.Model):
    """AI-generated summary for a code block."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("permanently_failed", "Permanently Failed"),
    ]

    block = models.OneToOneField(
        CodeBlock,
        on_delete=models.CASCADE,
        related_name="summary",
    )
    summary_text = models.TextField()
    summary_vector = SearchVectorField(null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    retry_count = models.IntegerField(default=0)
    language = models.CharField(max_length=10, default="en")
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "explorer_blocksummary"
        indexes = []  # GinIndex only used with PostgreSQL

    def __str__(self):
        return f"Summary for {self.block.name}"


def _generate_share_token():
    """Generate a cryptographically random URL-safe token (at least 22 chars)."""
    return secrets.token_urlsafe(24)  # Produces 32 URL-safe characters


class SharedView(models.Model):
    """A publicly accessible shared view of a repository."""

    repository = models.OneToOneField(
        Repository,
        on_delete=models.CASCADE,
        related_name="shared_view",
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        default=_generate_share_token,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "explorer_sharedview"

    def __str__(self):
        return f"SharedView for {self.repository.name} (active={self.is_active})"


class UsageStats(models.Model):
    """Tracks usage statistics per user for MVP caps and analytics."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="usage_stats",
    )
    repos_created = models.IntegerField(default=0)
    files_processed = models.IntegerField(default=0)
    summaries_generated = models.IntegerField(default=0)

    class Meta:
        db_table = "explorer_usagestats"

    def __str__(self):
        return f"UsageStats for {self.user.username}"


class SummarizationJob(models.Model):
    """Tracks the state of individual summarization jobs."""

    JOB_TYPE_CHOICES = [
        ("file", "File"),
        ("block", "Block"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("permanently_failed", "Permanently Failed"),
    ]

    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="summarization_jobs",
    )
    file = models.ForeignKey(
        RepositoryFile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="summarization_jobs",
    )
    block = models.ForeignKey(
        CodeBlock,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="summarization_jobs",
    )
    job_type = models.CharField(max_length=10, choices=JOB_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    retry_count = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "explorer_summarizationjob"
        indexes = [
            models.Index(
                fields=["repository", "status"],
                name="sumjob_repo_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.job_type} job ({self.status})"
