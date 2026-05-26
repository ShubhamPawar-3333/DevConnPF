"""
Celery tasks for repository ingestion and parsing.

Handles background cloning of GitHub repositories, file storage,
code parsing with tree-sitter, and progress tracking via Redis.
"""

import logging
import os

import redis
import requests
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings

from explorer.encryption import TokenEncryptionService
from explorer.models import Repository, RepositoryFile, User, UsageStats

logger = logging.getLogger(__name__)

# Maximum repository size (500 MB)
MAX_REPO_SIZE_BYTES = 500 * 1024 * 1024

# MVP hard cap: max files per repository
MAX_FILES_PER_REPO = 200

# Redis key prefix for ingestion progress
PROGRESS_KEY_PREFIX = "ingestion"


def _get_redis_client():
    """Get a Redis client using the configured REDIS_URL."""
    return redis.from_url(settings.REDIS_URL)


def _update_progress(repository_id, stage, detail=None, files_processed=0, total_files=0):
    """Update ingestion progress in Redis.

    Args:
        repository_id: The Repository ID.
        stage: Current stage (e.g., "cloning", "fetching_tree", "storing_files").
        detail: Optional detail message.
        files_processed: Number of files processed so far.
        total_files: Total number of files to process.
    """
    try:
        r = _get_redis_client()
        key = f"{PROGRESS_KEY_PREFIX}:{repository_id}:progress"
        progress_data = {
            "stage": stage,
            "files_processed": str(files_processed),
            "total_files": str(total_files),
        }
        if detail:
            progress_data["detail"] = detail
        r.hset(key, mapping=progress_data)
        # Expire progress data after 1 hour
        r.expire(key, 3600)
    except Exception as e:
        logger.warning(
            "Failed to update progress in Redis for repo %s: %s",
            repository_id,
            str(e),
        )


@shared_task(
    bind=True,
    soft_time_limit=300,  # 5-minute soft timeout
    time_limit=330,  # 5.5-minute hard timeout (grace period)
    max_retries=0,  # No automatic retries; user can manually retry
    acks_late=True,
)
def clone_repository_task(self, repository_id, user_id):
    """Clone a GitHub repository and store its files.

    Fetches the repository contents via GitHub API (using the tree endpoint),
    stores files as RepositoryFile records, and updates Repository metadata.

    Args:
        repository_id: The ID of the Repository record.
        user_id: The ID of the User who initiated the ingestion.
    """
    try:
        repository = Repository.objects.get(id=repository_id)
        user = User.objects.get(id=user_id)
    except (Repository.DoesNotExist, User.DoesNotExist) as e:
        logger.error("Repository or User not found: %s", str(e))
        return

    try:
        # Decrypt user's GitHub token
        encryption_service = TokenEncryptionService()
        token = encryption_service.decrypt(bytes(user.github_token_encrypted))

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        }

        repo_full_name = repository.github_full_name

        _update_progress(repository_id, "cloning", "Fetching repository metadata...")

        # Step 1: Get repository info (default branch)
        repo_info = _fetch_repo_info(repo_full_name, headers)
        default_branch = repo_info.get("default_branch", "main")

        # Step 2: Get the latest commit SHA for the default branch
        commit_sha = _fetch_latest_commit_sha(repo_full_name, default_branch, headers)

        _update_progress(repository_id, "cloning", "Fetching file tree...")

        # Step 3: Get the full file tree recursively
        tree_items = _fetch_repo_tree(repo_full_name, commit_sha, headers)

        # Filter to only blob (file) items
        file_items = [item for item in tree_items if item.get("type") == "blob"]

        # Apply MVP cap: only process first 200 files
        files_capped = False
        total_file_count = len(file_items)
        if total_file_count > MAX_FILES_PER_REPO:
            logger.info(
                "Repository %s: capping file processing at %d files (total: %d).",
                repo_full_name,
                MAX_FILES_PER_REPO,
                total_file_count,
            )
            file_items = file_items[:MAX_FILES_PER_REPO]
            files_capped = True

        # Calculate total size and validate
        total_size = sum(item.get("size", 0) for item in file_items)
        if total_size > MAX_REPO_SIZE_BYTES:
            repository.status = "failed"
            repository.save(update_fields=["status"])
            _update_progress(
                repository_id,
                "failed",
                f"Repository exceeds 500 MB size limit ({total_size / (1024 * 1024):.1f} MB).",
            )
            return

        total_files = len(file_items)
        _update_progress(
            repository_id,
            "storing_files",
            f"Storing {total_files} files...",
            files_processed=0,
            total_files=total_files,
        )

        # Step 4: Fetch and store each file's content
        files_stored = 0
        total_size_stored = 0

        for item in file_items:
            file_path = item.get("path", "")
            file_size = item.get("size", 0)
            sha = item.get("sha", "")

            # Fetch file content via the blob API
            content = _fetch_file_content(repo_full_name, sha, headers)

            if content is not None:
                filename = os.path.basename(file_path)
                language = _detect_language_from_extension(filename)

                RepositoryFile.objects.create(
                    repository=repository,
                    path=file_path,
                    filename=filename,
                    language=language,
                    content=content,
                    size_bytes=file_size,
                    is_summarizable=_is_summarizable(filename),
                )

                files_stored += 1
                total_size_stored += file_size

                # Update progress every 10 files
                if files_stored % 10 == 0:
                    _update_progress(
                        repository_id,
                        "storing_files",
                        f"Stored {files_stored}/{total_files} files...",
                        files_processed=files_stored,
                        total_files=total_files,
                    )

        # Step 5: Update repository metadata
        repository.branch = default_branch
        repository.commit_sha = commit_sha
        repository.file_count = files_stored
        repository.total_size_bytes = total_size_stored
        repository.status = "parsing"
        repository.save(
            update_fields=[
                "branch",
                "commit_sha",
                "file_count",
                "total_size_bytes",
                "status",
            ]
        )

        # Update usage stats for files processed
        try:
            usage_stats, _ = UsageStats.objects.get_or_create(user=user)
            usage_stats.files_processed += files_stored
            usage_stats.save(update_fields=["files_processed"])
        except Exception as e:
            logger.warning(
                "Failed to update usage stats for repo %s: %s",
                repository_id,
                str(e),
            )

        detail_msg = f"Cloning complete. {files_stored} files stored."
        if files_capped:
            detail_msg += (
                f" Note: Only the first {MAX_FILES_PER_REPO} files were processed "
                f"due to the per-repository file limit (total in repo: {total_file_count})."
            )

        _update_progress(
            repository_id,
            "parsing",
            detail_msg,
            files_processed=files_stored,
            total_files=total_files,
        )

        logger.info(
            "Successfully cloned repository %s (%d files, %d bytes)",
            repo_full_name,
            files_stored,
            total_size_stored,
        )

        # Trigger parsing stage
        parse_repository_task.delay(repository_id)

    except SoftTimeLimitExceeded:
        logger.error(
            "Clone operation timed out for repository %s (5-minute limit exceeded)",
            repository_id,
        )
        repository.status = "failed"
        repository.save(update_fields=["status"])
        _update_progress(
            repository_id,
            "failed",
            "Clone operation timed out (5-minute limit exceeded). You may retry.",
        )

    except requests.RequestException as e:
        logger.error(
            "Network error while cloning repository %s: %s",
            repository_id,
            str(e),
        )
        repository.status = "failed"
        repository.save(update_fields=["status"])
        _update_progress(
            repository_id,
            "failed",
            f"Network error: {str(e)}. Please check connectivity and retry.",
        )

    except Exception as e:
        logger.error(
            "Unexpected error while cloning repository %s: %s",
            repository_id,
            str(e),
        )
        repository.status = "failed"
        repository.save(update_fields=["status"])
        _update_progress(
            repository_id,
            "failed",
            f"Unexpected error: {str(e)}",
        )


def _fetch_repo_info(repo_full_name, headers):
    """Fetch repository metadata from GitHub API.

    Args:
        repo_full_name: The full repository name (e.g., "owner/repo").
        headers: Authorization headers for the GitHub API.

    Returns:
        A dict containing repository metadata.

    Raises:
        requests.RequestException: On network errors.
        IngestionError: On API errors.
    """
    url = f"https://api.github.com/repos/{repo_full_name}"
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def _fetch_latest_commit_sha(repo_full_name, branch, headers):
    """Fetch the latest commit SHA for a branch.

    Args:
        repo_full_name: The full repository name.
        branch: The branch name.
        headers: Authorization headers.

    Returns:
        The commit SHA string.

    Raises:
        requests.RequestException: On network errors.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/commits/{branch}"
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json().get("sha", "")


def _fetch_repo_tree(repo_full_name, commit_sha, headers):
    """Fetch the full repository tree recursively.

    Args:
        repo_full_name: The full repository name.
        commit_sha: The commit SHA to fetch the tree for.
        headers: Authorization headers.

    Returns:
        A list of tree items (dicts with path, type, size, sha).

    Raises:
        requests.RequestException: On network errors.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/git/trees/{commit_sha}?recursive=1"
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data.get("tree", [])


def _fetch_file_content(repo_full_name, blob_sha, headers):
    """Fetch a file's content from GitHub via the blob API.

    Uses the raw media type to get the file content directly.

    Args:
        repo_full_name: The full repository name.
        blob_sha: The blob SHA for the file.
        headers: Authorization headers.

    Returns:
        The file content as a string, or None if the file is binary/too large.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/git/blobs/{blob_sha}"
    # Request raw content
    fetch_headers = {**headers, "Accept": "application/vnd.github.raw+json"}

    try:
        response = requests.get(url, headers=fetch_headers, timeout=30)
        response.raise_for_status()

        # Try to decode as text; skip binary files
        try:
            content = response.content.decode("utf-8")
            return content
        except UnicodeDecodeError:
            # Binary file, skip it
            return None

    except requests.RequestException as e:
        logger.warning("Failed to fetch blob %s: %s", blob_sha, str(e))
        return None


def _detect_language_from_extension(filename):
    """Detect programming language from file extension.

    Args:
        filename: The filename to detect language for.

    Returns:
        A language string or "unknown".
    """
    extension_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".c": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".rb": "ruby",
        ".php": "php",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".xml": "xml",
        ".sql": "sql",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "zsh",
        ".swift": "swift",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".scala": "scala",
        ".r": "r",
        ".R": "r",
        ".lua": "lua",
        ".dart": "dart",
        ".vue": "vue",
        ".svelte": "svelte",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".cs": "csharp",
        ".fs": "fsharp",
        ".ex": "elixir",
        ".exs": "elixir",
        ".erl": "erlang",
        ".hs": "haskell",
        ".clj": "clojure",
    }

    _, ext = os.path.splitext(filename)
    return extension_map.get(ext.lower(), "unknown")


def _is_summarizable(filename):
    """Determine if a file should be summarized.

    Returns False for binary files, lock files, minified bundles,
    and other auto-generated files.

    Args:
        filename: The filename to check.

    Returns:
        True if the file should be summarized, False otherwise.
    """
    # Non-summarizable extensions (binary, media, etc.)
    non_summarizable_extensions = {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
        ".mp3", ".mp4", ".wav", ".avi", ".mov", ".webm",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx",
        ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
        ".exe", ".dll", ".so", ".dylib", ".o", ".a",
        ".woff", ".woff2", ".ttf", ".eot", ".otf",
        ".pyc", ".pyo", ".class", ".jar",
        ".db", ".sqlite", ".sqlite3",
    }

    # Non-summarizable filename patterns (lock files, minified, etc.)
    non_summarizable_names = {
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "Pipfile.lock",
        "poetry.lock",
        "Gemfile.lock",
        "composer.lock",
        "Cargo.lock",
        "go.sum",
    }

    # Check exact filename matches
    if filename in non_summarizable_names:
        return False

    # Check for minified files
    if ".min." in filename:
        return False

    # Check extension
    _, ext = os.path.splitext(filename)
    if ext.lower() in non_summarizable_extensions:
        return False

    # Check if it has a recognized programming extension
    recognized_extensions = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs",
        ".c", ".cpp", ".cc", ".h", ".hpp", ".rb", ".php",
        ".html", ".htm", ".css", ".scss", ".sass", ".less",
        ".md", ".json", ".yaml", ".yml", ".xml", ".sql",
        ".sh", ".bash", ".zsh", ".swift", ".kt", ".kts",
        ".scala", ".r", ".R", ".lua", ".dart", ".vue", ".svelte",
        ".toml", ".ini", ".cfg", ".cs", ".fs", ".ex", ".exs",
        ".erl", ".hs", ".clj",
    }

    if ext.lower() in recognized_extensions:
        return True

    return False


@shared_task(
    bind=True,
    soft_time_limit=600,  # 10-minute soft timeout
    time_limit=660,  # 11-minute hard timeout
    max_retries=0,
    acks_late=True,
)
def parse_repository_task(self, repository_id):
    """Parse all stored files in a repository and trigger summarization.

    For each RepositoryFile:
    - Detects the language using tree-sitter language detection
    - Determines if the file is summarizable
    - Parses the file with tree-sitter to extract code blocks
    - Stores extracted code blocks in the database

    After all files are parsed, enqueues summarization jobs for all
    summarizable files and their code blocks.

    Args:
        repository_id: The ID of the Repository record.
    """
    from explorer.parsing import CodeParser, store_code_blocks
    from explorer.summarization import enqueue_summarization_jobs

    try:
        repository = Repository.objects.get(id=repository_id)
    except Repository.DoesNotExist:
        logger.error("Repository %d not found for parsing.", repository_id)
        return

    try:
        parser = CodeParser()

        # Get all files for this repository
        files = RepositoryFile.objects.filter(repository=repository)
        total_files = files.count()

        _update_progress(
            repository_id,
            "parsing",
            f"Parsing {total_files} files...",
            files_processed=0,
            total_files=total_files,
        )

        files_parsed = 0

        for repo_file in files.iterator():
            # Detect language using tree-sitter detection
            language = parser.detect_language(repo_file.filename)

            # Determine if the file is summarizable
            is_summarizable = parser.is_summarizable_file(repo_file.filename)

            # Update file metadata
            update_fields = ["is_summarizable"]
            repo_file.is_summarizable = is_summarizable

            if language:
                repo_file.language = language
                update_fields.append("language")

            repo_file.save(update_fields=update_fields)

            # Parse the file with tree-sitter if it has a supported language
            if language and is_summarizable and repo_file.content:
                try:
                    code_blocks = parser.parse_file(repo_file.content, language)
                    if code_blocks:
                        store_code_blocks(repo_file, code_blocks)
                except Exception as e:
                    logger.warning(
                        "Failed to parse file %s (repo %d): %s",
                        repo_file.path,
                        repository_id,
                        str(e),
                    )

            files_parsed += 1

            # Update progress every 10 files
            if files_parsed % 10 == 0:
                _update_progress(
                    repository_id,
                    "parsing",
                    f"Parsed {files_parsed}/{total_files} files...",
                    files_processed=files_parsed,
                    total_files=total_files,
                )

        _update_progress(
            repository_id,
            "parsing",
            f"Parsing complete. {files_parsed} files processed.",
            files_processed=files_parsed,
            total_files=total_files,
        )

        logger.info(
            "Parsing complete for repository %d: %d files processed.",
            repository_id,
            files_parsed,
        )

        # Get the user's language preference for summarization
        language_preference = repository.user.language_preference

        # Enqueue summarization jobs (this also updates status to "summarizing")
        jobs_enqueued = enqueue_summarization_jobs(repository_id, language_preference)

        logger.info(
            "Enqueued %d summarization jobs for repository %d.",
            jobs_enqueued,
            repository_id,
        )

        # If no jobs were enqueued (no summarizable files), mark as ready
        if jobs_enqueued == 0:
            repository.refresh_from_db()
            repository.status = "ready"
            repository.save(update_fields=["status", "updated_at"])
            _update_progress(
                repository_id,
                "ready",
                "No summarizable files found. Repository is ready.",
            )

    except SoftTimeLimitExceeded:
        logger.error(
            "Parsing timed out for repository %d (10-minute limit exceeded).",
            repository_id,
        )
        repository.status = "failed"
        repository.save(update_fields=["status"])
        _update_progress(
            repository_id,
            "failed",
            "Parsing timed out (10-minute limit exceeded). You may retry.",
        )

    except Exception as e:
        logger.error(
            "Unexpected error during parsing for repository %d: %s",
            repository_id,
            str(e),
        )
        repository.status = "failed"
        repository.save(update_fields=["status"])
        _update_progress(
            repository_id,
            "failed",
            f"Parsing failed: {str(e)}",
        )
