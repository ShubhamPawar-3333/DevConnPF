"""
Repository ingestion service for the AI Codebase Explorer.

Handles ingestion from GitHub repositories and ZIP file uploads.
Validates inputs, creates Repository records, and dispatches
background Celery tasks for processing.
"""

import logging
import os
import struct
import tempfile
import zipfile
from pathlib import Path

import redis
import requests
from celery import shared_task
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from .encryption import TokenEncryptionService
from .models import Repository, RepositoryFile, UsageStats

logger = logging.getLogger(__name__)

# Size limits
MAX_COMPRESSED_SIZE_BYTES = 200 * 1024 * 1024  # 200 MB
MAX_UNCOMPRESSED_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_REPO_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB (for GitHub repos)
MAX_FILE_COUNT = 10_000

# MVP hard caps
MAX_REPOS_PER_USER = 3
MAX_FILES_PER_REPO = 200

# ZIP magic bytes
ZIP_MAGIC_BYTES = b"PK\x03\x04"

# End of Central Directory signature
EOCD_SIGNATURE = b"PK\x05\x06"

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"


def _get_redis_client():
    """Get a Redis client for progress tracking."""
    return redis.from_url(settings.REDIS_URL)


def _update_progress(repository_id: int, stage: str, detail: str = ""):
    """Update ingestion progress in Redis."""
    try:
        client = _get_redis_client()
        key = f"ingestion:{repository_id}:progress"
        client.hset(key, mapping={
            "stage": stage,
            "detail": detail,
            "updated_at": timezone.now().isoformat(),
        })
        # Expire after 1 hour
        client.expire(key, 3600)
    except Exception as e:
        logger.warning(f"Failed to update progress in Redis: {e}")


class ZipValidationError(Exception):
    """Raised when ZIP validation fails."""
    pass


class IngestionError(Exception):
    """Raised when ingestion encounters an error."""
    pass


class TokenPermissionError(IngestionError):
    """Raised when the user's GitHub token lacks required permissions."""
    pass


class RepoSizeExceededError(IngestionError):
    """Raised when the repository exceeds the maximum allowed size."""
    pass


class RepoAlreadyExistsError(IngestionError):
    """Raised when the repository has already been ingested for this user."""

    def __init__(self, existing_repository):
        self.existing_repository = existing_repository
        super().__init__(
            f"Repository '{existing_repository.github_full_name}' already exists."
        )


class RepoLimitExceededError(IngestionError):
    """Raised when the user has reached the maximum number of repositories."""

    def __init__(self, max_repos=MAX_REPOS_PER_USER):
        super().__init__(
            f"You have reached the maximum limit of {max_repos} repositories. "
            f"Please delete an existing repository before adding a new one."
        )


class IngestionService:
    """Service for ingesting repositories from GitHub or ZIP uploads."""

    def __init__(self):
        self.encryption_service = TokenEncryptionService()

    def ingest_from_github(self, user, repo_full_name, force_reingest=False):
        """Ingest a GitHub repository for the given user.

        Validates the user's token permissions, checks repository size,
        creates a Repository record with status "cloning", and dispatches
        the clone_repository_task.

        Args:
            user: The User instance initiating the ingestion.
            repo_full_name: The full repository name (e.g., "owner/repo").
            force_reingest: If True, replace existing data for this repo.

        Returns:
            The created Repository instance.

        Raises:
            TokenPermissionError: If the user's token lacks repo read access.
            RepoSizeExceededError: If the repository exceeds 500 MB.
            RepoAlreadyExistsError: If the repo already exists and force_reingest is False.
            IngestionError: For other ingestion failures.
        """
        # Decrypt the user's GitHub token
        token = self._get_user_token(user)

        # Check repository limit (3 repos per user)
        current_repo_count = Repository.objects.filter(user=user).count()
        if current_repo_count >= MAX_REPOS_PER_USER:
            # Don't count against limit if re-ingesting an existing repo
            existing = Repository.objects.filter(
                user=user,
                github_full_name=repo_full_name,
                source_type="github",
            ).first()
            if not (existing and force_reingest):
                raise RepoLimitExceededError()

        # Check for existing repository
        existing = Repository.objects.filter(
            user=user,
            github_full_name=repo_full_name,
            source_type="github",
        ).first()

        if existing and not force_reingest:
            raise RepoAlreadyExistsError(existing)

        # Validate token permissions and get repo metadata
        repo_data = self._validate_and_fetch_repo(token, repo_full_name)

        # Check repository size (GitHub reports size in KB)
        repo_size_bytes = repo_data.get("size", 0) * 1024
        if repo_size_bytes > MAX_REPO_SIZE_BYTES:
            raise RepoSizeExceededError(
                f"Repository '{repo_full_name}' is {repo_size_bytes / (1024 * 1024):.1f} MB, "
                f"which exceeds the maximum allowed size of 500 MB."
            )

        # If re-ingesting, delete old data
        if existing and force_reingest:
            existing.delete()

        # Create Repository record with status "cloning"
        repository = Repository.objects.create(
            user=user,
            name=repo_data.get("name", repo_full_name.split("/")[-1]),
            source_type="github",
            github_full_name=repo_full_name,
            status="cloning",
        )

        # Update usage stats
        usage_stats, _ = UsageStats.objects.get_or_create(user=user)
        usage_stats.repos_created += 1
        usage_stats.save(update_fields=["repos_created"])

        # Dispatch the clone task
        from explorer.tasks import clone_repository_task

        clone_repository_task.delay(repository.id, user.id)

        return repository

    def _get_user_token(self, user):
        """Decrypt and return the user's GitHub access token.

        Args:
            user: The User instance.

        Returns:
            The decrypted GitHub access token string.

        Raises:
            IngestionError: If the user has no stored token.
        """
        if not user.github_token_encrypted:
            raise IngestionError(
                "No GitHub token found. Please re-authenticate with GitHub."
            )
        return self.encryption_service.decrypt(bytes(user.github_token_encrypted))

    def _validate_and_fetch_repo(self, token, repo_full_name):
        """Validate token permissions and fetch repository metadata from GitHub.

        Args:
            token: The decrypted GitHub access token.
            repo_full_name: The full repository name (e.g., "owner/repo").

        Returns:
            A dict containing the repository metadata from GitHub API.

        Raises:
            TokenPermissionError: If the token lacks required permissions.
            IngestionError: If the GitHub API is unavailable or returns an error.
        """
        url = f"{GITHUB_API_BASE}/repos/{repo_full_name}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
        except requests.RequestException as e:
            raise IngestionError(
                f"Failed to connect to GitHub API: {str(e)}. "
                "Please check your network connection and try again."
            )

        if response.status_code == 401:
            raise TokenPermissionError(
                "Your GitHub token is invalid or expired. "
                "Please re-authenticate with GitHub."
            )
        elif response.status_code == 403:
            raise TokenPermissionError(
                "Your GitHub token lacks the required permissions to access this repository. "
                "Please ensure your token has 'repo' scope for private repositories."
            )
        elif response.status_code == 404:
            raise TokenPermissionError(
                f"Repository '{repo_full_name}' not found. "
                "Ensure the repository exists and your token has read access."
            )
        elif response.status_code != 200:
            raise IngestionError(
                f"GitHub API returned unexpected status {response.status_code}. "
                "Please try again later."
            )

        return response.json()

    def ingest_from_zip(self, user, zip_file: UploadedFile) -> Repository:
        """
        Ingest a repository from a ZIP file upload.

        Validates the ZIP format (magic bytes + central directory),
        validates compressed size <= 200MB, creates a Repository record
        with status "extracting", and dispatches extract_zip_task.

        Args:
            user: The authenticated user performing the upload.
            zip_file: The uploaded ZIP file.

        Returns:
            The created Repository instance.

        Raises:
            ZipValidationError: If the file is not a valid ZIP or exceeds size limits.
        """
        # Validate compressed size
        file_size = zip_file.size
        if file_size > MAX_COMPRESSED_SIZE_BYTES:
            raise ZipValidationError(
                f"ZIP file exceeds maximum compressed size of 200 MB. "
                f"File size: {file_size / (1024 * 1024):.1f} MB."
            )

        # Check repository limit (3 repos per user)
        current_repo_count = Repository.objects.filter(user=user).count()
        if current_repo_count >= MAX_REPOS_PER_USER:
            raise RepoLimitExceededError()

        # Validate ZIP format (magic bytes)
        zip_file.seek(0)
        header = zip_file.read(4)
        zip_file.seek(0)

        if header != ZIP_MAGIC_BYTES:
            raise ZipValidationError(
                "The uploaded file is not a valid ZIP archive. "
                "Please upload a file in ZIP format."
            )

        # Validate central directory structure
        if not self._has_valid_central_directory(zip_file):
            raise ZipValidationError(
                "The uploaded file is not a valid ZIP archive. "
                "The file is missing a valid central directory structure."
            )

        # Get original filename
        original_filename = getattr(zip_file, "name", "upload.zip") or "upload.zip"
        repo_name = Path(original_filename).stem

        # Save the ZIP to a temporary file for async processing
        temp_dir = tempfile.mkdtemp(prefix="explorer_zip_")
        temp_path = os.path.join(temp_dir, original_filename)

        zip_file.seek(0)
        with open(temp_path, "wb") as f:
            for chunk in zip_file.chunks():
                f.write(chunk)

        # Create Repository record with status "extracting"
        repository = Repository.objects.create(
            user=user,
            name=repo_name,
            source_type="zip",
            original_filename=original_filename,
            status="extracting",
        )

        # Update usage stats
        usage_stats, _ = UsageStats.objects.get_or_create(user=user)
        usage_stats.repos_created += 1
        usage_stats.save(update_fields=["repos_created"])

        # Update progress
        _update_progress(repository.id, "uploading", "Upload complete, starting extraction")

        # Dispatch Celery task
        extract_zip_task.delay(repository.id, temp_path)

        return repository

    def _has_valid_central_directory(self, zip_file: UploadedFile) -> bool:
        """
        Check if the ZIP file has a valid End of Central Directory record.

        The EOCD record is located at the end of the ZIP file. We search
        backwards from the end for the EOCD signature (PK\\x05\\x06).

        Args:
            zip_file: The uploaded file to validate.

        Returns:
            True if a valid central directory is found, False otherwise.
        """
        zip_file.seek(0, 2)  # Seek to end
        file_size = zip_file.tell()

        if file_size < 22:  # Minimum EOCD size
            return False

        # EOCD can be at most 65535 + 22 bytes from the end (max comment length)
        search_start = max(0, file_size - 65557)
        search_length = file_size - search_start

        zip_file.seek(search_start)
        data = zip_file.read(search_length)
        zip_file.seek(0)

        # Search for EOCD signature from the end
        eocd_offset = data.rfind(EOCD_SIGNATURE)
        if eocd_offset == -1:
            return False

        # Verify EOCD has enough bytes after signature (minimum 18 bytes after sig)
        if len(data) - eocd_offset < 22:
            return False

        return True

    def validate_repository_size(self, size_bytes: int) -> bool:
        """Validate that repository size is within limits."""
        return size_bytes <= MAX_REPO_SIZE_BYTES

    @staticmethod
    def validate_repository_size_static(size_bytes: int) -> bool:
        """Validate that repository size is within limits (static version)."""
        return size_bytes <= MAX_REPO_SIZE_BYTES


@shared_task(bind=True, max_retries=0, time_limit=600, soft_time_limit=300)
def extract_zip_task(self, repository_id: int, file_path: str) -> None:
    """
    Celery task to extract a ZIP archive and store files.

    Extracts the archive, validates uncompressed size <= 500MB and
    file count <= 10,000, stores files in RepositoryFile records,
    and updates repository metadata.

    On failure, discards partial data (deletes Repository and any
    partial RepositoryFile records).

    Args:
        repository_id: The ID of the Repository record.
        file_path: Path to the temporary ZIP file on disk.
    """
    repository = None
    try:
        repository = Repository.objects.get(id=repository_id)

        _update_progress(repository_id, "extracting", "Extracting ZIP archive")

        # Open and validate the ZIP
        if not zipfile.is_zipfile(file_path):
            raise ZipValidationError("File is not a valid ZIP archive.")

        with zipfile.ZipFile(file_path, "r") as zf:
            # Validate uncompressed size
            total_uncompressed = sum(info.file_size for info in zf.infolist())
            if total_uncompressed > MAX_UNCOMPRESSED_SIZE_BYTES:
                raise ZipValidationError(
                    f"Extracted contents exceed maximum uncompressed size of 500 MB. "
                    f"Uncompressed size: {total_uncompressed / (1024 * 1024):.1f} MB."
                )

            # Get list of files (exclude directories)
            file_entries = [
                info for info in zf.infolist()
                if not info.is_dir()
            ]

            # Validate file count
            if len(file_entries) > MAX_FILE_COUNT:
                raise ZipValidationError(
                    f"ZIP archive contains more than {MAX_FILE_COUNT:,} files. "
                    f"File count: {len(file_entries):,}."
                )

            # Apply MVP cap: only process first 200 summarizable files
            files_capped = False
            if len(file_entries) > MAX_FILES_PER_REPO:
                logger.info(
                    f"Repository {repository_id}: capping file processing at "
                    f"{MAX_FILES_PER_REPO} files (total: {len(file_entries)})."
                )
                file_entries = file_entries[:MAX_FILES_PER_REPO]
                files_capped = True

            _update_progress(
                repository_id, "storing",
                f"Storing {len(file_entries)} files"
            )

            # Store files in database
            total_size = 0
            file_records = []

            for info in file_entries:
                # Skip directories and empty entries
                if info.is_dir():
                    continue

                # Read file content
                try:
                    content_bytes = zf.read(info.filename)
                except Exception as e:
                    logger.warning(
                        f"Skipping file {info.filename} in repo {repository_id}: {e}"
                    )
                    continue

                # Try to decode as text; skip binary files
                try:
                    content = content_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        content = content_bytes.decode("latin-1")
                    except UnicodeDecodeError:
                        # Skip binary files
                        continue

                file_size = len(content_bytes)
                total_size += file_size

                # Extract filename from path
                file_path_str = info.filename
                filename = Path(file_path_str).name

                file_records.append(
                    RepositoryFile(
                        repository=repository,
                        path=file_path_str,
                        filename=filename,
                        language="unknown",  # Will be detected during parsing
                        content=content,
                        size_bytes=file_size,
                        is_summarizable=True,  # Will be refined during parsing
                    )
                )

            # Bulk create file records
            with transaction.atomic():
                RepositoryFile.objects.bulk_create(file_records, batch_size=500)

                # Update repository metadata
                repository.file_count = len(file_records)
                repository.total_size_bytes = total_size
                repository.status = "parsing"
                repository.save(
                    update_fields=["file_count", "total_size_bytes", "status", "updated_at"]
                )

        # Update usage stats for files processed
        try:
            usage_stats, _ = UsageStats.objects.get_or_create(user=repository.user)
            usage_stats.files_processed += len(file_records)
            usage_stats.save(update_fields=["files_processed"])
        except Exception as e:
            logger.warning(f"Failed to update usage stats for repo {repository_id}: {e}")

        detail_msg = f"Complete. {len(file_records)} files stored."
        if files_capped:
            detail_msg += (
                f" Note: Only the first {MAX_FILES_PER_REPO} files were processed "
                f"due to the per-repository file limit."
            )

        _update_progress(
            repository_id, "storing",
            detail_msg
        )

        logger.info(
            f"ZIP extraction complete for repository {repository_id}: "
            f"{len(file_records)} files, {total_size} bytes"
        )

        # Trigger parsing stage
        from explorer.tasks import parse_repository_task
        parse_repository_task.delay(repository_id)

    except ZipValidationError as e:
        logger.error(f"ZIP validation failed for repository {repository_id}: {e}")
        _discard_partial_data(repository_id)
        raise

    except Repository.DoesNotExist:
        logger.error(f"Repository {repository_id} not found for ZIP extraction.")
        raise

    except Exception as e:
        logger.error(
            f"Unexpected error during ZIP extraction for repository {repository_id}: {e}"
        )
        _discard_partial_data(repository_id)
        raise

    finally:
        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
            # Try to remove the temp directory
            temp_dir = os.path.dirname(file_path)
            if os.path.isdir(temp_dir) and temp_dir.startswith(tempfile.gettempdir()):
                os.rmdir(temp_dir)
        except OSError as e:
            logger.warning(f"Failed to clean up temp file {file_path}: {e}")


def _discard_partial_data(repository_id: int) -> None:
    """
    Discard partial data on failure.

    Deletes the Repository record and any associated RepositoryFile records.
    The CASCADE delete on the FK handles RepositoryFile cleanup.
    """
    try:
        repository = Repository.objects.get(id=repository_id)
        repository.status = "failed"
        repository.save(update_fields=["status", "updated_at"])
        logger.info(f"Marked repository {repository_id} as failed.")
    except Repository.DoesNotExist:
        logger.warning(
            f"Repository {repository_id} not found when discarding partial data."
        )
