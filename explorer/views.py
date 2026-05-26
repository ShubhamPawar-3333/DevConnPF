"""
Explorer views for authentication and API endpoints.
"""

import logging
from collections import defaultdict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from explorer.auth_services import GitHubOAuthService
from explorer.ingestion import (
    IngestionError,
    IngestionService,
    RepoAlreadyExistsError,
    RepoLimitExceededError,
    RepoSizeExceededError,
    TokenPermissionError,
    ZipValidationError,
)
from explorer.models import (
    BlockSummary,
    CodeBlock,
    FileSummary,
    Repository,
    RepositoryFile,
    SharedView,
    SummarizationJob,
    User,
)
from explorer.progress import ProgressService
from explorer.search import QueryValidationError, SummarySearchService
from explorer.sharing import SharingService
from explorer.summarization import summarize_block_task, summarize_file_task

logger = logging.getLogger(__name__)


def _github_oauth_redirect_uri():
    """Return the callback URI registered with the GitHub OAuth app."""
    return f"{settings.FRONTEND_URL.rstrip('/')}/auth/callback"


@require_GET
def login_view(request):
    """Redirect the user to GitHub OAuth authorization.

    If the user is already authenticated, redirect to the home page.
    Otherwise, initiate the GitHub OAuth flow via social-auth-app-django.
    """
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    # Use social-auth's built-in begin URL for GitHub
    return redirect("social:begin", backend="github")


@api_view(["GET"])
@permission_classes([AllowAny])
def github_auth_url_view(request):
    """Return the app-local GitHub login URL for the frontend.

    This deliberately routes through Django's social-auth flow instead of
    constructing a separate SPA callback flow. GitHub OAuth apps only allow
    one callback URL, and this project is configured for Django's backend
    callback: /auth/complete/github/.

    URL: GET /api/auth/github/url/

    Response:
        200: {"url": "/api/auth/github/"}
    """
    return Response({"url": "/api/auth/github/"}, status=status.HTTP_200_OK)


def oauth_callback_view(request):
    """Handle the OAuth callback from GitHub.

    This view handles errors that social-auth-app-django redirects to.
    The actual token exchange is handled by social-auth's complete URL.
    This view is configured as SOCIAL_AUTH_LOGIN_ERROR_URL to catch OAuth errors.

    Possible error scenarios:
    - User denied authorization
    - Invalid or expired authorization code
    - Network/GitHub API errors
    """
    error = request.GET.get("error")
    error_description = request.GET.get("error_description", "")

    if error == "access_denied":
        messages.error(
            request,
            "GitHub authorization was denied. Please try again and approve access to continue.",
        )
    elif error:
        messages.error(
            request,
            f"GitHub authentication failed: {error_description or error}. Please try again.",
        )
    else:
        # Generic error from social-auth pipeline
        messages.error(
            request,
            "Authentication failed. The authorization code may be invalid or expired. "
            "Please try signing in again.",
        )

    return redirect("explorer:login")


@require_POST
def logout_view(request):
    """Sign out the user: invalidate session, delete token, redirect to landing.

    Steps:
    1. Revoke the GitHub token (best-effort)
    2. Clear the encrypted token from the user model
    3. Invalidate the Django session
    4. Redirect to the landing page
    """
    if request.user.is_authenticated:
        try:
            oauth_service = GitHubOAuthService()
            oauth_service.revoke_token(request.user)
        except Exception as e:
            logger.warning("Error during token revocation on logout: %s", str(e))

        logout(request)

    return redirect("/")



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def repository_progress_view(request, repository_id):
    """Get summarization progress for a repository.

    Returns the count of completed, pending, and failed summarization jobs
    along with the derived repository status.

    Only the repository owner can access this endpoint.

    URL: GET /api/repositories/{id}/progress/

    Response:
        200: {total, completed, pending, failed, status}
        403: User does not own this repository
        404: Repository not found
    """
    try:
        repository = Repository.objects.get(id=repository_id)
    except Repository.DoesNotExist:
        return Response(
            {"error": "Repository not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Ensure the authenticated user owns this repository
    if repository.user_id != request.user.id:
        return Response(
            {"error": "You do not have permission to access this repository."},
            status=status.HTTP_403_FORBIDDEN,
        )

    progress_service = ProgressService()
    progress = progress_service.get_progress(repository_id)

    return Response(
        {
            "total": progress.total_jobs,
            "completed": progress.completed,
            "pending": progress.pending,
            "failed": progress.failed,
            "status": progress.status,
        },
        status=status.HTTP_200_OK,
    )


def _get_summary_status(file_obj):
    """Get the summary status for a file.

    Returns a tuple of (status, can_retry).
    """
    try:
        summary = file_obj.summary
        return summary.status, summary.status in ("failed", "permanently_failed")
    except FileSummary.DoesNotExist:
        return "pending", False


def _truncate_summary(summary_text, max_length=80):
    """Truncate summary text to max_length characters with ellipsis."""
    if not summary_text:
        return ""
    if len(summary_text) <= max_length:
        return summary_text
    return summary_text[: max_length - 3] + "..."


def sort_tree_entries(entries):
    """Sort tree entries: directories before files, alphabetical case-insensitive within each group.

    Args:
        entries: List of dicts with at least 'type' and 'name' keys.

    Returns:
        Sorted list with directories first, then files, each group sorted
        alphabetically (case-insensitive).
    """
    directories = [e for e in entries if e["type"] == "directory"]
    files = [e for e in entries if e["type"] == "file"]

    directories.sort(key=lambda x: x["name"].lower())
    files.sort(key=lambda x: x["name"].lower())

    return directories + files


def _build_file_tree(repository):
    """Build a nested directory tree structure from repository files.

    Returns a list of root-level entries (directories and files) with
    subdirectories collapsed (children included but not recursively expanded
    in the initial response — all data is present for client-side expansion).
    """
    files = repository.files.select_related("summary").defer("content").all()

    # Build a tree structure using nested dicts
    # tree[path] = {children: [...], ...}
    tree = defaultdict(lambda: {"children": [], "type": "directory"})
    root_children = []

    # Track which paths we've already added as entries
    added_dirs = set()

    for file_obj in files:
        path = file_obj.path
        parts = path.split("/")

        # Get summary info
        summary_status, can_retry = _get_summary_status(file_obj)
        summary_preview = ""
        try:
            if file_obj.summary and file_obj.summary.status == "completed":
                summary_preview = _truncate_summary(file_obj.summary.summary_text)
        except FileSummary.DoesNotExist:
            pass

        file_entry = {
            "id": file_obj.id,
            "name": file_obj.filename,
            "path": file_obj.path,
            "type": "file",
            "summary_preview": summary_preview,
            "summary_status": summary_status,
            "can_retry": can_retry,
        }

        if len(parts) == 1:
            # Root-level file
            root_children.append(file_entry)
        else:
            # File is inside directories
            # Ensure all parent directories exist in the tree
            for i in range(len(parts) - 1):
                dir_path = "/".join(parts[: i + 1])
                dir_name = parts[i]

                if dir_path not in added_dirs:
                    added_dirs.add(dir_path)

                    dir_entry = {
                        "name": dir_name,
                        "path": dir_path,
                        "type": "directory",
                        "children": [],
                    }

                    if i == 0:
                        # Root-level directory
                        root_children.append(dir_entry)
                        tree[dir_path] = dir_entry
                    else:
                        # Nested directory
                        parent_path = "/".join(parts[:i])
                        tree[parent_path]["children"].append(dir_entry)
                        tree[dir_path] = dir_entry

            # Add file to its parent directory
            parent_path = "/".join(parts[:-1])
            tree[parent_path]["children"].append(file_entry)

    # Sort all directory children recursively
    def sort_children(entries):
        sorted_entries = sort_tree_entries(entries)
        for entry in sorted_entries:
            if entry["type"] == "directory" and "children" in entry:
                entry["children"] = sort_children(entry["children"])
        return sorted_entries

    return sort_children(root_children)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def repository_tree_view(request, repository_id):
    """Get the file tree for a repository.

    Returns the complete directory hierarchy with root-level items visible,
    subdirectories collapsed, directories sorted before files (alphabetical,
    case-insensitive), and truncated File_Summary preview (80 chars) next to
    each file.

    Only the repository owner can access this endpoint.

    URL: GET /api/repositories/{id}/tree/

    Response:
        200: {tree: [...nested directory structure...]}
        403: User does not own this repository
        404: Repository not found
    """
    try:
        repository = Repository.objects.get(id=repository_id)
    except Repository.DoesNotExist:
        return Response(
            {"error": "Repository not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Ensure the authenticated user owns this repository
    if repository.user_id != request.user.id:
        return Response(
            {"error": "You do not have permission to access this repository."},
            status=status.HTTP_403_FORBIDDEN,
        )

    tree = _build_file_tree(repository)

    return Response(
        {
            "repository_id": repository.id,
            "repository_name": repository.name,
            "status": repository.status,
            "tree": tree,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def file_detail_view(request, repository_id, file_id):
    """Get full file summary and block summaries for a file.

    Returns the file info, full File_Summary text, and list of Block_Summaries
    for the selected file. Includes summary status and retry option for files
    marked as "summary unavailable".

    Only the repository owner can access this endpoint.

    URL: GET /api/repositories/{id}/files/{file_id}/

    Response:
        200: {file info, summary, blocks}
        403: User does not own this repository
        404: Repository or file not found
    """
    try:
        repository = Repository.objects.get(id=repository_id)
    except Repository.DoesNotExist:
        return Response(
            {"error": "Repository not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Ensure the authenticated user owns this repository
    if repository.user_id != request.user.id:
        return Response(
            {"error": "You do not have permission to access this repository."},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        file_obj = RepositoryFile.objects.get(id=file_id, repository=repository)
    except RepositoryFile.DoesNotExist:
        return Response(
            {"error": "File not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Get file summary
    summary_data = None
    can_retry = False
    try:
        summary = file_obj.summary
        summary_data = {
            "summary_text": summary.summary_text if summary.status == "completed" else None,
            "status": summary.status,
            "language": summary.language,
            "generated_at": summary.generated_at,
        }
        can_retry = summary.status in ("failed", "permanently_failed")
    except FileSummary.DoesNotExist:
        summary_data = {
            "summary_text": None,
            "status": "pending",
            "language": None,
            "generated_at": None,
        }

    # Get block summaries
    blocks = file_obj.code_blocks.select_related("summary").all()
    block_list = []
    for block in blocks:
        block_entry = {
            "id": block.id,
            "name": block.name,
            "kind": block.kind,
            "start_line": block.start_line,
            "end_line": block.end_line,
            "parent_block_name": block.parent_block_name,
        }

        try:
            block_summary = block.summary
            block_entry["summary_text"] = (
                block_summary.summary_text
                if block_summary.status == "completed"
                else None
            )
            block_entry["summary_status"] = block_summary.status
        except BlockSummary.DoesNotExist:
            block_entry["summary_text"] = None
            block_entry["summary_status"] = "pending"

        block_list.append(block_entry)

    return Response(
        {
            "id": file_obj.id,
            "path": file_obj.path,
            "filename": file_obj.filename,
            "language": file_obj.language,
            "size_bytes": file_obj.size_bytes,
            "summary": summary_data,
            "can_retry": can_retry,
            "blocks": block_list,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def block_detail_view(request, repository_id, block_id):
    """Get source code and block summary for a code block.

    Returns the block info, source code, and Block_Summary for the selected
    code block.

    Only the repository owner can access this endpoint.

    URL: GET /api/repositories/{id}/blocks/{block_id}/

    Response:
        200: {block info, source_code, summary}
        403: User does not own this repository
        404: Repository or block not found
    """
    try:
        repository = Repository.objects.get(id=repository_id)
    except Repository.DoesNotExist:
        return Response(
            {"error": "Repository not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Ensure the authenticated user owns this repository
    if repository.user_id != request.user.id:
        return Response(
            {"error": "You do not have permission to access this repository."},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        block = CodeBlock.objects.select_related("file", "summary").get(
            id=block_id, file__repository=repository
        )
    except CodeBlock.DoesNotExist:
        return Response(
            {"error": "Code block not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Get block summary
    summary_data = None
    try:
        block_summary = block.summary
        summary_data = {
            "summary_text": (
                block_summary.summary_text
                if block_summary.status == "completed"
                else None
            ),
            "status": block_summary.status,
            "language": block_summary.language,
            "generated_at": block_summary.generated_at,
        }
    except BlockSummary.DoesNotExist:
        summary_data = {
            "summary_text": None,
            "status": "pending",
            "language": None,
            "generated_at": None,
        }

    return Response(
        {
            "id": block.id,
            "name": block.name,
            "kind": block.kind,
            "start_line": block.start_line,
            "end_line": block.end_line,
            "parent_block_name": block.parent_block_name,
            "source_code": block.content,
            "file_path": block.file.path,
            "file_id": block.file.id,
            "summary": summary_data,
        },
        status=status.HTTP_200_OK,
    )


# Supported language codes for summaries
SUPPORTED_LANGUAGES = {"en", "es", "fr", "de", "pt", "ja", "ko", "zh"}


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def language_preference_view(request):
    """Update the authenticated user's language preference.

    Accepts a supported language code and persists it on the User model.
    Defaults to "en" when no preference has been explicitly set.

    URL: PUT /api/users/me/language/

    Request body:
        {"language": "es"}

    Response:
        200: {"language": "<code>", "message": "Language preference updated."}
        400: Invalid or missing language code
    """
    language = request.data.get("language")

    if not language:
        return Response(
            {"error": "Language code is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if language not in SUPPORTED_LANGUAGES:
        return Response(
            {
                "error": f"Unsupported language code '{language}'. "
                f"Supported languages: {', '.join(sorted(SUPPORTED_LANGUAGES))}."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = request.user
    user.language_preference = language
    user.save(update_fields=["language_preference"])

    return Response(
        {"language": language, "message": "Language preference updated."},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def regenerate_summaries_view(request, repository_id):
    """Regenerate all summaries for a repository in the user's current language.

    Re-enqueues summarization jobs for all summarizable files and code blocks.
    Previous summaries remain available for browsing until regeneration completes,
    at which point they are replaced by the new summaries.

    Only the repository owner can trigger regeneration.

    URL: POST /api/repositories/{id}/regenerate-summaries/

    Response:
        202: {"message": "...", "jobs_enqueued": N, "language": "<code>"}
        403: User does not own this repository
        404: Repository not found
    """
    try:
        repository = Repository.objects.get(id=repository_id)
    except Repository.DoesNotExist:
        return Response(
            {"error": "Repository not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Only the repository owner can trigger regeneration
    if repository.user_id != request.user.id:
        return Response(
            {"error": "You do not have permission to regenerate summaries for this repository."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Get the user's current language preference
    language = request.user.language_preference or "en"

    # Delete existing SummarizationJob records for this repository
    # (previous summaries on FileSummary/BlockSummary remain until new ones complete)
    SummarizationJob.objects.filter(repository=repository).delete()

    # Update repository status to summarizing
    repository.status = "summarizing"
    repository.save(update_fields=["status"])

    # Re-enqueue summarization jobs for all summarizable files and their code blocks
    jobs_enqueued = 0

    summarizable_files = RepositoryFile.objects.filter(
        repository=repository,
        is_summarizable=True,
    )

    for file in summarizable_files:
        # Create a new SummarizationJob for the file
        SummarizationJob.objects.create(
            repository=repository,
            file=file,
            job_type="file",
            status="pending",
        )
        summarize_file_task.delay(file.id, language)
        jobs_enqueued += 1

        # Create SummarizationJobs for each code block in the file
        code_blocks = CodeBlock.objects.filter(file=file)
        for block in code_blocks:
            SummarizationJob.objects.create(
                repository=repository,
                block=block,
                file=file,
                job_type="block",
                status="pending",
            )
            summarize_block_task.delay(block.id, language)
            jobs_enqueued += 1

    logger.info(
        "Regeneration started for repository %d: %d jobs enqueued with language '%s'.",
        repository_id,
        jobs_enqueued,
        language,
    )

    return Response(
        {
            "message": f"Summary regeneration started. {jobs_enqueued} jobs enqueued.",
            "jobs_enqueued": jobs_enqueued,
            "language": language,
        },
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def repository_search_view(request, repository_id):
    """Search across summaries within a repository.

    Uses full-text search to find matching File_Summaries and Block_Summaries
    ranked by textual similarity. Returns highlighted excerpts with file paths
    and block names.

    Only the repository owner can search.

    URL: GET /api/repositories/{id}/search/?q=<query>

    Query Parameters:
        q: Search query string (3-300 characters)

    Response:
        200: {results: [...], count: N} or {results: [], message: "..."}
        400: Invalid query (too short, too long, or missing)
        403: User does not own this repository
        404: Repository not found
    """
    try:
        repository = Repository.objects.get(id=repository_id)
    except Repository.DoesNotExist:
        return Response(
            {"error": "Repository not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Ensure the authenticated user owns this repository
    if repository.user_id != request.user.id:
        return Response(
            {"error": "You do not have permission to access this repository."},
            status=status.HTTP_403_FORBIDDEN,
        )

    query = request.query_params.get("q", "")

    # Validate query
    search_service = SummarySearchService()
    try:
        results = search_service.search(repository_id, query)
    except QueryValidationError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Return results
    if not results:
        return Response(
            {
                "results": [],
                "count": 0,
                "message": "No matches found. Try refining your query with different keywords.",
            },
            status=status.HTTP_200_OK,
        )

    results_data = [
        {
            "file_path": r.file_path,
            "block_name": r.block_name,
            "summary_excerpt": r.summary_excerpt,
            "similarity_rank": r.similarity_rank,
            "result_type": r.result_type,
        }
        for r in results
    ]

    return Response(
        {
            "results": results_data,
            "count": len(results_data),
        },
        status=status.HTTP_200_OK,
    )


# --- Sharing Endpoints ---


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def repository_share_view(request, repository_id):
    """Enable or disable sharing for a repository.

    POST: Enable sharing — generates a unique share URL.
    DELETE: Disable sharing — invalidates the share URL (404 within 5 seconds).

    Only the repository owner can manage sharing.

    URL: POST /api/repositories/{id}/share/
    URL: DELETE /api/repositories/{id}/share/

    Response (POST):
        200: {"token": "...", "share_url": "/api/shared/{token}/", "is_active": true}
        404: Repository not found
        403: User does not own this repository

    Response (DELETE):
        200: {"message": "Sharing disabled."}
        404: Repository not found
        403: User does not own this repository
    """
    try:
        repository = Repository.objects.get(id=repository_id)
    except Repository.DoesNotExist:
        return Response(
            {"error": "Repository not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if repository.user_id != request.user.id:
        return Response(
            {"error": "You do not have permission to manage sharing for this repository."},
            status=status.HTTP_403_FORBIDDEN,
        )

    sharing_service = SharingService()

    if request.method == "POST":
        shared_view = sharing_service.enable_sharing(repository)
        return Response(
            {
                "token": shared_view.token,
                "share_url": f"/api/shared/{shared_view.token}/",
                "is_active": shared_view.is_active,
            },
            status=status.HTTP_200_OK,
        )
    else:
        # DELETE
        sharing_service.disable_sharing(repository)
        return Response(
            {"message": "Sharing disabled."},
            status=status.HTTP_200_OK,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def repository_share_regenerate_view(request, repository_id):
    """Regenerate the share URL for a repository.

    Creates a new token and immediately invalidates the old one.

    Only the repository owner can regenerate the share URL.

    URL: POST /api/repositories/{id}/share/regenerate/

    Response:
        200: {"token": "...", "share_url": "/api/shared/{token}/", "is_active": true}
        404: Repository not found
        403: User does not own this repository
    """
    try:
        repository = Repository.objects.get(id=repository_id)
    except Repository.DoesNotExist:
        return Response(
            {"error": "Repository not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if repository.user_id != request.user.id:
        return Response(
            {"error": "You do not have permission to manage sharing for this repository."},
            status=status.HTTP_403_FORBIDDEN,
        )

    sharing_service = SharingService()
    shared_view = sharing_service.regenerate_url(repository)

    return Response(
        {
            "token": shared_view.token,
            "share_url": f"/api/shared/{shared_view.token}/",
            "is_active": shared_view.is_active,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def shared_repository_view(request, token):
    """Public endpoint to view a shared repository.

    Displays the File_Tree_Browser with all summaries in read-only mode,
    with Summary_Search enabled and an attribution banner showing the
    repository owner's username.

    No authentication required.

    URL: GET /api/shared/{token}/

    Response:
        200: {repository info, tree, attribution, search_enabled}
        404: Invalid token, inactive share, or deleted repository
    """
    sharing_service = SharingService()
    repository = sharing_service.get_shared_repository(token)

    if repository is None:
        return Response(
            {"error": "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Build the file tree for the shared repository
    tree = _build_file_tree(repository)

    # Get owner username for attribution banner
    owner_username = repository.user.username

    return Response(
        {
            "repository_id": repository.id,
            "repository_name": repository.name,
            "status": repository.status,
            "owner_username": owner_username,
            "attribution": f"Shared by {owner_username}",
            "search_enabled": True,
            "read_only": True,
            "tree": tree,
            "branding": "Powered by DevConnPf",
        },
        status=status.HTTP_200_OK,
    )


# =============================================================================
# Missing endpoints needed by the frontend
# =============================================================================


@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([AllowAny])
def current_user_view(request):
    """Return the current auth session state.

    URL: GET /api/auth/me/

    Response:
        200: {isAuthenticated, user}
    """
    if not request.user.is_authenticated:
        return Response(
            {
                "isAuthenticated": False,
                "user": None,
            },
            status=status.HTTP_200_OK,
        )

    user = request.user
    # Try to get avatar URL from social auth
    avatar_url = None
    try:
        social = user.social_auth.filter(provider="github").first()
        if social and social.extra_data:
            avatar_url = social.extra_data.get("avatar_url")
    except Exception:
        pass

    return Response(
        {
            "isAuthenticated": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email or "",
                "languagePreference": user.language_preference,
                "avatarUrl": avatar_url,
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def repository_list_or_create_view(request):
    """List or create repositories.

    GET: List all repositories owned by the authenticated user.
    POST: Create/ingest a new repository.
    """
    if request.method == "GET":
        return _repository_list_response(request)

    return _repository_create_response(request)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def repository_list_view(request):
    """List all repositories owned by the authenticated user.

    URL: GET /api/repositories/

    Response:
        200: [{id, name, sourceType, status, fileCount, ...}, ...]
    """
    return _repository_list_response(request)


def _repository_list_response(request):
    repositories = (
        Repository.objects.filter(user=request.user)
        .select_related("shared_view")
        .order_by("-ingested_at")
    )

    data = []
    for repo in repositories:
        # Check for share info
        share_info = None
        try:
            shared_view = repo.shared_view
            if shared_view.is_active:
                share_info = {
                    "token": shared_view.token,
                    "url": f"/shared/{shared_view.token}",
                    "isActive": shared_view.is_active,
                    "createdAt": shared_view.created_at.isoformat(),
                }
        except SharedView.DoesNotExist:
            pass

        data.append(
            {
                "id": repo.id,
                "name": repo.name,
                "sourceType": repo.source_type,
                "githubFullName": repo.github_full_name,
                "status": repo.status,
                "fileCount": repo.file_count,
                "totalSizeBytes": repo.total_size_bytes,
                "ingestedAt": repo.ingested_at.isoformat(),
                "updatedAt": repo.updated_at.isoformat(),
                "shareInfo": share_info,
            }
        )

    return Response(data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def repository_create_view(request):
    """Create/ingest a new repository.

    Accepts either a GitHub URL or a ZIP file upload.
    Enforces the 3-repository limit per user.

    URL: POST /api/repositories/

    Request body (JSON):
        {"github_url": "https://github.com/owner/repo"}

    Response:
        202: {"repository_id": N}
        400: Validation error
        403: Repository limit reached
    """
    return _repository_create_response(request)


def _repository_create_response(request):
    service = IngestionService()

    try:
        zip_file = request.FILES.get("zip_file")
        if zip_file is not None:
            repository = service.ingest_from_zip(request.user, zip_file)
            return Response(
                {"repository_id": repository.id},
                status=status.HTTP_202_ACCEPTED,
            )

        github_url = request.data.get("github_url")
        if not github_url:
            return Response(
                {"message": "github_url or zip_file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        github_full_name = _extract_github_full_name(github_url)
        if github_full_name is None:
            return Response(
                {"message": "Invalid GitHub URL format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        repository = service.ingest_from_github(request.user, github_full_name)
        return Response(
            {"repository_id": repository.id},
            status=status.HTTP_202_ACCEPTED,
        )
    except RepoLimitExceededError as e:
        return Response({"message": str(e)}, status=status.HTTP_403_FORBIDDEN)
    except RepoAlreadyExistsError as e:
        return Response(
            {
                "message": str(e),
                "repository_id": e.existing_repository.id,
            },
            status=status.HTTP_409_CONFLICT,
        )
    except TokenPermissionError as e:
        return Response({"message": str(e)}, status=status.HTTP_403_FORBIDDEN)
    except (ZipValidationError, RepoSizeExceededError) as e:
        return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except IngestionError as e:
        return Response({"message": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


def _extract_github_full_name(github_url):
    """Return owner/repo from a GitHub URL, or None when the URL is invalid."""
    if not isinstance(github_url, str):
        return None

    cleaned_url = github_url.strip()
    if not url_has_allowed_host_and_scheme(
        cleaned_url,
        allowed_hosts={"github.com", "www.github.com"},
        require_https=False,
    ):
        return None

    parts = cleaned_url.rstrip("/").split("/")
    if len(parts) < 2:
        return None

    owner = parts[-2]
    repo = parts[-1]
    if not owner or not repo or owner == "github.com":
        return None

    if repo.endswith(".git"):
        repo = repo[:-4]

    return f"{owner}/{repo}"


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def repository_delete_view(request, repository_id):
    """Delete a repository owned by the authenticated user.

    URL: DELETE /api/repositories/{id}/

    Response:
        204: Successfully deleted
        403: User does not own this repository
        404: Repository not found
    """
    try:
        repository = Repository.objects.get(id=repository_id)
    except Repository.DoesNotExist:
        return Response(
            {"error": "Repository not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if repository.user_id != request.user.id:
        return Response(
            {"error": "You do not have permission to delete this repository."},
            status=status.HTTP_403_FORBIDDEN,
        )

    repository.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([AllowAny])
def github_callback_api_view(request):
    """API endpoint for the frontend to exchange an OAuth code for a session.

    The frontend sends the authorization code received from GitHub,
    and this endpoint exchanges it for an access token, creates/updates
    the user, and establishes a Django session.

    URL: POST /api/auth/github/callback/

    Request body:
        {"code": "...", "state": "..."}

    Response:
        200: {"user": {id, username, email, languagePreference, avatarUrl}}
        400: Invalid code or exchange failed
    """
    import requests as http_requests
    from django.contrib.auth import login as auth_login
    from explorer.encryption import TokenEncryptionService

    code = request.data.get("code")
    returned_state = request.data.get("state")

    if not code:
        return Response(
            {"error": "missing_code", "detail": "Authorization code is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    expected_state = request.session.get("oauth_state")
    if expected_state and returned_state != expected_state:
        return Response(
            {"error": "invalid_state", "detail": "OAuth state validation failed."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if expected_state:
        request.session.pop("oauth_state", None)

    # Exchange the authorization code for an access token with GitHub
    client_id = settings.SOCIAL_AUTH_GITHUB_KEY
    client_secret = settings.SOCIAL_AUTH_GITHUB_SECRET

    if not client_id or not client_secret:
        return Response(
            {"error": "server_config_error", "detail": "GitHub OAuth is not configured."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    try:
        token_response = http_requests.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": _github_oauth_redirect_uri(),
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        token_data = token_response.json()
    except Exception as e:
        logger.error("Failed to exchange OAuth code: %s", str(e))
        return Response(
            {"error": "exchange_failed", "detail": "Failed to communicate with GitHub."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if "error" in token_data:
        error_desc = token_data.get("error_description", token_data["error"])
        return Response(
            {"error": token_data["error"], "detail": error_desc},
            status=status.HTTP_400_BAD_REQUEST,
        )

    access_token = token_data.get("access_token")
    if not access_token:
        return Response(
            {"error": "no_token", "detail": "No access token in GitHub response."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Fetch the user's GitHub profile
    try:
        user_response = http_requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=10,
        )
        if user_response.status_code != 200:
            return Response(
                {"error": "github_api_error", "detail": "Failed to fetch GitHub user profile."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        github_user = user_response.json()
    except Exception as e:
        logger.error("Failed to fetch GitHub user: %s", str(e))
        return Response(
            {"error": "github_api_error", "detail": "Failed to fetch GitHub user profile."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    github_username = github_user.get("login", "")
    github_email = github_user.get("email") or ""
    avatar_url = github_user.get("avatar_url", "")
    github_id = github_user.get("id")

    # Get or create the user
    user = User.objects.filter(username=github_username).first()
    if user is None:
        user = User.objects.create_user(
            username=github_username,
            email=github_email,
        )

    # Update email if it changed
    if github_email and user.email != github_email:
        user.email = github_email
        user.save(update_fields=["email"])

    # Encrypt and store the access token
    try:
        encryption_service = TokenEncryptionService()
        encrypted_token = encryption_service.encrypt(access_token)
        user.github_token_encrypted = encrypted_token
        user.save(update_fields=["github_token_encrypted"])
    except Exception as e:
        logger.warning("Failed to store encrypted token for user %s: %s", user.username, str(e))

    # Update or create social_auth association for avatar_url
    try:
        from social_django.models import UserSocialAuth

        social, _ = UserSocialAuth.objects.get_or_create(
            user=user,
            provider="github",
            defaults={"uid": str(github_id), "extra_data": {}},
        )
        social.uid = str(github_id)
        if not social.extra_data:
            social.extra_data = {}
        social.extra_data["avatar_url"] = avatar_url
        social.extra_data["access_token"] = access_token
        social.save()
    except Exception as e:
        logger.warning("Failed to update social auth for user %s: %s", user.username, str(e))

    # Establish a Django session
    auth_login(request._request, user, backend="social_core.backends.github.GithubOAuth2")

    return Response(
        {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email or "",
                "languagePreference": user.language_preference,
                "avatarUrl": avatar_url,
            }
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_logout_view(request):
    """API logout endpoint — revokes token, clears session, returns JSON.

    URL: POST /api/auth/logout/

    Response:
        200: {"message": "Logged out successfully."}
    """
    if request.user.is_authenticated:
        try:
            oauth_service = GitHubOAuthService()
            oauth_service.revoke_token(request.user)
        except Exception as e:
            logger.warning("Error during token revocation on logout: %s", str(e))

        logout(request)

    return Response(
        {"message": "Logged out successfully."},
        status=status.HTTP_200_OK,
    )
