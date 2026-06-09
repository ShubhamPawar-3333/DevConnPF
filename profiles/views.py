"""
Profile API views.

Implements all REST endpoints for the developer profiles feature.
Authentication uses CorsSessionAuthentication (session cookies, no CSRF
enforcement) in line with the existing explorer app pattern.
"""

import logging
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from explorer.authentication import CorsSessionAuthentication  # noqa: F401 – loaded by DRF via DEFAULT_AUTHENTICATION_CLASSES
from explorer.models import Repository
from profiles.models import Follow, Profile, ProjectEntry
from profiles.serializers import (
    FollowSerializer,
    ProfileOwnerSerializer,
    ProfilePublicSerializer,
    ProjectEntrySerializer,
)
from profiles.services import (
    FollowService,
    GitHubImportError,
    GitHubImportService,
    GitHubTokenMissingError,
    ProfileService,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_valid_url(value: str) -> bool:
    """Return True if *value* is a well-formed HTTP(S) URL."""
    try:
        result = urlparse(value)
        return result.scheme in ("http", "https") and bool(result.netloc)
    except Exception:
        return False


def _validate_profile_fields(data: dict, partial: bool = False) -> dict:
    """Validate profile field values from a request payload.

    Args:
        data: The request data dict.
        partial: When True (PATCH), only fields present in *data* are
                 validated.  When False (PUT/POST), required fields are
                 checked for presence.

    Returns:
        A dict mapping field names to lists of error strings.  An empty
        dict means validation passed.
    """
    errors: dict[str, list[str]] = {}

    # --- display_name ---
    if "display_name" in data or not partial:
        display_name = data.get("display_name", "")
        if not display_name:
            errors.setdefault("display_name", []).append("Display name is required.")
        elif not (2 <= len(display_name) <= 100):
            errors.setdefault("display_name", []).append(
                "Display name must be between 2 and 100 characters."
            )

    # --- bio ---
    if "bio" in data:
        bio = data["bio"]
        if bio is not None and len(bio) > 500:
            errors.setdefault("bio", []).append("Bio must be 500 characters or fewer.")

    # --- location ---
    if "location" in data:
        location = data["location"]
        if location is not None and len(location) > 100:
            errors.setdefault("location", []).append(
                "Location must be 100 characters or fewer."
            )

    # --- website_url ---
    if "website_url" in data:
        website_url = data["website_url"]
        if website_url:
            if len(website_url) > 200:
                errors.setdefault("website_url", []).append(
                    "Website URL must be 200 characters or fewer."
                )
            elif not _is_valid_url(website_url):
                errors.setdefault("website_url", []).append(
                    "Enter a valid HTTP or HTTPS URL."
                )

    # --- avatar_url ---
    if "avatar_url" in data:
        avatar_url = data["avatar_url"]
        if avatar_url:
            if not _is_valid_url(avatar_url):
                errors.setdefault("avatar_url", []).append(
                    "Enter a valid HTTP or HTTPS URL."
                )

    # --- skill_tags ---
    if "skill_tags" in data:
        skill_tags = data["skill_tags"]
        if skill_tags is not None:
            if not isinstance(skill_tags, list):
                errors.setdefault("skill_tags", []).append(
                    "skill_tags must be a list of strings."
                )
            else:
                if len(skill_tags) > 20:
                    errors.setdefault("skill_tags", []).append(
                        "You may have at most 20 skill tags."
                    )
                for tag in skill_tags:
                    if not isinstance(tag, str):
                        errors.setdefault("skill_tags", []).append(
                            "Each skill tag must be a string."
                        )
                        break
                    if len(tag) > 50:
                        errors.setdefault("skill_tags", []).append(
                            f"Each skill tag must be 50 characters or fewer (got '{tag[:50]}…')."
                        )
                        break

    return errors


# ---------------------------------------------------------------------------
# Task 4.1 — Profile creation + retrieval of own profile
# POST /api/profiles/me/  — create profile
# GET  /api/profiles/me/  — get own profile (owner view)
# ---------------------------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def create_profile_view(request):
    """Create (POST) or retrieve (GET) the authenticated user's profile.

    GET:  Returns the owner's profile if it exists, 404 otherwise.
    POST: Creates a new profile for the authenticated user.
    """
    if request.method == "GET":
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response(
                {"error": "Profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ProfileOwnerSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST — create a new profile
    # Prevent duplicate profiles
    if hasattr(request.user, "profile"):
        return Response(
            {"error": "Profile already exists."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = request.data

    # Validate common fields (non-partial — all required fields are checked)
    field_errors = _validate_profile_fields(data, partial=False)

    # Validate slug separately via ProfileService
    slug = data.get("slug", "")
    if not slug:
        field_errors.setdefault("slug", []).append("Slug is required.")
    else:
        try:
            ProfileService().validate_slug(slug)
        except ValidationError as exc:
            field_errors.setdefault("slug", []).extend(
                exc.messages if hasattr(exc, "messages") else [str(exc)]
            )

    if field_errors:
        return Response(
            {"error": "Validation failed", "fields": field_errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Build creation kwargs
    create_kwargs = {
        "user": request.user,
        "slug": slug,
        "display_name": data["display_name"],
        "github_username": request.user.username,
    }

    if "bio" in data:
        create_kwargs["bio"] = data["bio"]
    if "location" in data:
        create_kwargs["location"] = data["location"]
    if "website_url" in data:
        create_kwargs["website_url"] = data["website_url"] or None
    if "skill_tags" in data and data["skill_tags"] is not None:
        create_kwargs["skill_tags"] = data["skill_tags"]

    profile = Profile.objects.create(**create_kwargs)

    serializer = ProfileOwnerSerializer(profile)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Task 4.2 — Profile retrieval
# GET /api/profiles/<slug>/
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([AllowAny])
def get_profile_view(request, slug):
    """Retrieve a developer profile by slug.

    Returns the owner view when the authenticated user is the profile owner,
    and the public view for everyone else.

    URL: GET /api/profiles/<slug>/

    Response:
        200: ProfileOwnerSerializer | ProfilePublicSerializer
        404: Profile not found or inactive
    """
    try:
        profile = Profile.objects.get(slug=slug, status="active")
    except Profile.DoesNotExist:
        return Response(
            {"error": "Profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.user.is_authenticated and request.user == profile.user:
        serializer = ProfileOwnerSerializer(profile)
    else:
        serializer = ProfilePublicSerializer(profile)

    return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Task 4.3 — Profile update
# PUT /api/profiles/<slug>/update/
# PATCH /api/profiles/<slug>/update/
# ---------------------------------------------------------------------------

@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_profile_view(request, slug):
    """Update a developer profile.

    Only the profile owner may update.  PUT replaces provided fields; PATCH
    updates only the fields present in the request body.

    URL: PUT  /api/profiles/<slug>/update/
         PATCH /api/profiles/<slug>/update/

    Response:
        200: ProfileOwnerSerializer
        400: {"error": "Validation failed", "fields": {...}}
        403: {"error": "You do not have permission to edit this profile."}
        404: Profile not found or inactive
    """
    try:
        profile = Profile.objects.get(slug=slug, status="active")
    except Profile.DoesNotExist:
        return Response(
            {"error": "Profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.user != profile.user:
        return Response(
            {"error": "You do not have permission to edit this profile."},
            status=status.HTTP_403_FORBIDDEN,
        )

    data = request.data
    is_partial = request.method == "PATCH"

    # Validate common fields
    field_errors = _validate_profile_fields(data, partial=is_partial)

    # Validate slug if it's being changed
    if "slug" in data:
        new_slug = data["slug"]
        if not new_slug:
            field_errors.setdefault("slug", []).append("Slug cannot be empty.")
        else:
            try:
                ProfileService().validate_slug(new_slug, exclude_profile_id=profile.pk)
            except ValidationError as exc:
                field_errors.setdefault("slug", []).extend(
                    exc.messages if hasattr(exc, "messages") else [str(exc)]
                )

    if field_errors:
        return Response(
            {"error": "Validation failed", "fields": field_errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Apply updates — only touch fields present in the request body
    updatable_fields = [
        "display_name",
        "slug",
        "bio",
        "location",
        "website_url",
        "avatar_url",
        "skill_tags",
    ]

    changed_fields = []
    for field in updatable_fields:
        if field in data:
            value = data[field]
            # Normalise empty string URL fields to None
            if field in ("website_url", "avatar_url") and value == "":
                value = None
            setattr(profile, field, value)
            changed_fields.append(field)

    if changed_fields:
        profile.save(update_fields=changed_fields + ["updated_at"])

    serializer = ProfileOwnerSerializer(profile)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Task 5.1 — GitHub import preview
# GET /api/profiles/me/github/preview/
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def github_import_preview_view(request):
    """Preview importable GitHub profile data.

    Fetches the authenticated user's GitHub profile and returns both the
    GitHub values and the current profile values for the same fields, so the
    frontend can show a side-by-side comparison before the user confirms.

    URL: GET /api/profiles/me/github/preview/

    Response:
        200: {
            "github_data": {"avatar_url": ..., "display_name": ..., "bio": ...},
            "current_profile": {"avatar_url": ..., "display_name": ..., "bio": ...}
        }
        400: {"error": "...", "action": "re-authenticate"} | {"error": "..."}
        404: Profile not found
    """
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return Response(
            {"error": "Profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        github_data = GitHubImportService().fetch_github_profile(request.user)
    except GitHubTokenMissingError as exc:
        return Response(
            {
                "error": str(exc),
                "action": "re-authenticate",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except GitHubImportError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    current_profile = {
        "avatar_url": profile.avatar_url,
        "display_name": profile.display_name,
        "bio": profile.bio,
    }

    return Response(
        {
            "github_data": github_data,
            "current_profile": current_profile,
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Task 5.2 — GitHub import apply
# POST /api/profiles/me/github/apply/
# ---------------------------------------------------------------------------

# Fields that can be imported from GitHub
_IMPORTABLE_FIELDS = frozenset(["avatar_url", "display_name", "bio"])


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def github_import_apply_view(request):
    """Apply selected GitHub profile data to the authenticated user's profile.

    The caller supplies a list of field names to import.  Only fields that are
    both requested *and* returned by GitHub (non-null) are applied.  All other
    profile fields remain unchanged.

    URL: POST /api/profiles/me/github/apply/

    Request body:
        {"fields": ["avatar_url", "display_name", "bio"]}  # any subset

    Response:
        200: ProfileOwnerSerializer
        400: token/API errors or validation failures
        404: Profile not found
    """
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return Response(
            {"error": "Profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    requested_fields = request.data.get("fields", [])
    if not isinstance(requested_fields, list):
        return Response(
            {"error": "Validation failed", "fields": {"fields": ["Must be a list of field names."]}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        github_data = GitHubImportService().fetch_github_profile(request.user)
    except GitHubTokenMissingError as exc:
        return Response(
            {
                "error": str(exc),
                "action": "re-authenticate",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except GitHubImportError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Determine fields to actually apply: requested ∩ importable ∩ returned-by-GitHub
    fields_to_apply = {
        f: github_data[f]
        for f in requested_fields
        if f in _IMPORTABLE_FIELDS and f in github_data and github_data[f]
    }

    if not fields_to_apply:
        # Nothing to apply — return current profile unchanged
        serializer = ProfileOwnerSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # Validate the values we're about to apply
    field_errors = _validate_profile_fields(fields_to_apply, partial=True)
    if field_errors:
        return Response(
            {"error": "Validation failed", "fields": field_errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    changed_fields = []
    for field, value in fields_to_apply.items():
        setattr(profile, field, value)
        changed_fields.append(field)

    profile.save(update_fields=changed_fields + ["updated_at"])

    serializer = ProfileOwnerSerializer(profile)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Task 6.1 — Add project endpoint
# POST /api/profiles/me/projects/
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_project_view(request):
    """Add a project to the authenticated user's profile.

    URL: POST /api/profiles/me/projects/

    Request body:
        {
            "repository_id": int,
            "custom_description": str (optional, max 300 chars)
        }

    Response:
        201: ProjectEntrySerializer
        400: validation errors
        404: profile not found
    """
    profile = get_object_or_404(Profile, user=request.user)

    # Validate repository_id
    repository_id = request.data.get("repository_id")
    if not repository_id:
        return Response(
            {"error": "repository_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        repository_id = int(repository_id)
    except (TypeError, ValueError):
        return Response(
            {"error": "repository_id must be an integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate custom_description if provided
    custom_description = request.data.get("custom_description", "")
    if custom_description and len(custom_description) > 300:
        return Response(
            {"error": "custom_description must be 300 characters or fewer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Fetch repository — must belong to authenticated user
    try:
        repository = Repository.objects.get(pk=repository_id, user=request.user)
    except Repository.DoesNotExist:
        return Response(
            {"error": "Repository is unavailable."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check project limit
    if profile.projects.count() >= 50:
        return Response(
            {"error": "Maximum project limit of 50 reached."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Create project entry
    try:
        from django.db import transaction
        with transaction.atomic():
            project_entry = ProjectEntry.objects.create(
                profile=profile,
                repository=repository,
                custom_description=custom_description or None,
                display_order=profile.projects.count(),
            )
    except IntegrityError:
        return Response(
            {"error": "This repository is already added to your profile."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = ProjectEntrySerializer(project_entry)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Task 6.2 — Remove project endpoint
# DELETE /api/profiles/me/projects/<project_id>/
# ---------------------------------------------------------------------------

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def remove_project_view(request, project_id):
    """Remove a project from the authenticated user's profile.

    URL: DELETE /api/profiles/me/projects/<project_id>/

    Response:
        204: No Content
        404: project not found or doesn't belong to user
    """
    profile = get_object_or_404(Profile, user=request.user)

    project_entry = get_object_or_404(
        ProjectEntry,
        pk=project_id,
        profile=profile,
    )

    project_entry.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Task 6.3 — Reorder projects endpoint
# PUT /api/profiles/me/projects/reorder/
# ---------------------------------------------------------------------------

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def reorder_projects_view(request):
    """Reorder projects on the authenticated user's profile.

    URL: PUT /api/profiles/me/projects/reorder/

    Request body:
        {
            "projects": [
                {"id": int, "display_order": int},
                ...
            ]
        }

    Response:
        200: list of ProjectEntrySerializer
        400: validation errors
        404: profile not found
    """
    profile = get_object_or_404(Profile, user=request.user)

    projects_data = request.data.get("projects", [])
    if not isinstance(projects_data, list):
        return Response(
            {"error": "projects must be a list."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate all project IDs belong to the authenticated user's profile
    project_ids = [p.get("id") for p in projects_data]
    user_project_ids = set(profile.projects.values_list("id", flat=True))

    for pid in project_ids:
        if pid not in user_project_ids:
            return Response(
                {"error": f"Project {pid} does not belong to your profile."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Update display_order for each project
    for project_data in projects_data:
        project_id = project_data.get("id")
        display_order = project_data.get("display_order")

        project_entry = ProjectEntry.objects.get(pk=project_id, profile=profile)
        project_entry.display_order = display_order
        project_entry.save(update_fields=["display_order"])

    # Return updated list
    serializer = ProjectEntrySerializer(
        profile.projects.all(),
        many=True,
    )
    return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Task 7.1 — Follow user endpoint
# POST /api/profiles/<slug>/follow/
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def follow_user_view(request, slug):
    """Follow a user by their profile slug.

    URL: POST /api/profiles/<slug>/follow/

    Response:
        201: FollowSerializer
        400: validation error (self-follow, no profile)
        404: target profile not found
    """
    # Get target profile
    target_profile = get_object_or_404(Profile, slug=slug, status="active")

    # Get authenticated user's profile
    try:
        my_profile = request.user.profile
    except Profile.DoesNotExist:
        return Response(
            {"error": "You must have a profile to follow other users."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Call FollowService
    try:
        follow_obj = FollowService().follow(follower=my_profile, target=target_profile)
    except ValidationError as exc:
        return Response(
            {"error": str(exc.message) if hasattr(exc, "message") else str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = FollowSerializer(follow_obj)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Task 7.2 — Unfollow user endpoint
# DELETE /api/profiles/<slug>/unfollow/
# ---------------------------------------------------------------------------

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def unfollow_user_view(request, slug):
    """Unfollow a user by their profile slug.

    URL: DELETE /api/profiles/<slug>/unfollow/

    Response:
        204: No Content
        400: no profile
        404: target profile not found or not following
    """
    # Get target profile
    target_profile = get_object_or_404(Profile, slug=slug, status="active")

    # Get authenticated user's profile
    try:
        my_profile = request.user.profile
    except Profile.DoesNotExist:
        return Response(
            {"error": "You must have a profile to unfollow users."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Call FollowService
    try:
        FollowService().unfollow(follower=my_profile, target=target_profile)
    except Follow.DoesNotExist:
        return Response(
            {"error": "You are not following this user."},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Task 7.3 — Followers list endpoint
# GET /api/profiles/<slug>/followers/?page=1&page_size=20
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([AllowAny])
def followers_list_view(request, slug):
    """Get paginated list of followers for a profile.

    URL: GET /api/profiles/<slug>/followers/?page=1&page_size=20

    Response:
        200: {"count": int, "next": str|null, "previous": str|null, "results": [...]}
        404: profile not found
    """
    profile = get_object_or_404(Profile, slug=slug, status="active")

    # Fetch followers
    followers = Follow.objects.filter(target=profile).select_related("follower").order_by("-created_at")

    # Pagination
    page_size = int(request.query_params.get("page_size", 20))
    page_size = min(page_size, 100)  # Max 100
    page_number = int(request.query_params.get("page", 1))

    paginator = Paginator(followers, page_size)
    page_obj = paginator.get_page(page_number)

    serializer = FollowSerializer(page_obj, many=True)

    return Response({
        "count": paginator.count,
        "next": page_obj.next_page_number() if page_obj.has_next() else None,
        "previous": page_obj.previous_page_number() if page_obj.has_previous() else None,
        "results": serializer.data,
    }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Task 7.4 — Following list endpoint
# GET /api/profiles/<slug>/following/?page=1&page_size=20
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([AllowAny])
def following_list_view(request, slug):
    """Get paginated list of profiles that a user is following.

    URL: GET /api/profiles/<slug>/following/?page=1&page_size=20

    Response:
        200: {"count": int, "next": str|null, "previous": str|null, "results": [...]}
        404: profile not found
    """
    profile = get_object_or_404(Profile, slug=slug, status="active")

    # Fetch following
    following = Follow.objects.filter(follower=profile).select_related("target").order_by("-created_at")

    # Pagination
    page_size = int(request.query_params.get("page_size", 20))
    page_size = min(page_size, 100)  # Max 100
    page_number = int(request.query_params.get("page", 1))

    paginator = Paginator(following, page_size)
    page_obj = paginator.get_page(page_number)

    serializer = FollowSerializer(page_obj, many=True)

    return Response({
        "count": paginator.count,
        "next": page_obj.next_page_number() if page_obj.has_next() else None,
        "previous": page_obj.previous_page_number() if page_obj.has_previous() else None,
        "results": serializer.data,
    }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Task 8.1 — Search profiles endpoint
# GET /api/profiles/search/?q=<query>&skill_tag=<tag>&page=1
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([AllowAny])
def search_profiles_view(request):
    """Search profiles by query string with optional skill_tag filter.

    URL: GET /api/profiles/search/?q=<query>&skill_tag=<tag>&page=1

    Response:
        200: {"count": int, "results": [...]}
        400: validation errors
    """
    query = request.query_params.get("q", "").strip()

    # Validate query
    if not query:
        return Response(
            {"error": "Search query is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(query) > 200:
        return Response(
            {"error": "Search query must be 200 characters or fewer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Filter active profiles
    profiles = Profile.objects.filter(status="active")

    # Apply skill_tag filter if provided
    skill_tag = request.query_params.get("skill_tag", "").strip()
    if skill_tag:
        # Use icontains for SQLite compatibility (JSONField contains not supported on SQLite)
        profiles = profiles.filter(skill_tags__icontains=skill_tag)

    # Apply search filter
    profiles = profiles.filter(
        Q(display_name__icontains=query)
        | Q(github_username__icontains=query)
        | Q(bio__icontains=query)
        | Q(skill_tags__icontains=query)
    ).order_by("slug")  # consistent ordering for pagination

    # Pagination
    page_size = 20
    page_number = int(request.query_params.get("page", 1))

    paginator = Paginator(profiles, page_size)
    page_obj = paginator.get_page(page_number)

    serializer = ProfilePublicSerializer(page_obj, many=True)

    return Response({
        "count": paginator.count,
        "results": serializer.data,
    }, status=status.HTTP_200_OK)
