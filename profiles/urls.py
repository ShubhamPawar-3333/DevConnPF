"""
URL configuration for the profiles app.
"""

from django.urls import path

from profiles.views import (
    add_project_view,
    create_profile_view,
    follow_user_view,
    followers_list_view,
    following_list_view,
    get_profile_view,
    github_import_apply_view,
    github_import_preview_view,
    remove_project_view,
    reorder_projects_view,
    search_profiles_view,
    unfollow_user_view,
    update_profile_view,
)

app_name = "profiles"

urlpatterns = [
    # --- Fixed-path routes MUST come before <slug:slug> patterns ---

    # Search and discovery (must be before <slug:slug>/ to avoid collision)
    path("search/", search_profiles_view, name="search_profiles"),

    # Authenticated user's own profile
    path("me/", create_profile_view, name="my_profile"),
    path("me/github/preview/", github_import_preview_view, name="github_import_preview"),
    path("me/github/apply/", github_import_apply_view, name="github_import_apply"),
    path("me/projects/", add_project_view, name="add_project"),
    path("me/projects/reorder/", reorder_projects_view, name="reorder_projects"),
    path("me/projects/<int:project_id>/", remove_project_view, name="remove_project"),

    # --- Dynamic slug routes ---
    path("<slug:slug>/", get_profile_view, name="get_profile"),
    path("<slug:slug>/update/", update_profile_view, name="update_profile"),
    path("<slug:slug>/follow/", follow_user_view, name="follow_user"),
    path("<slug:slug>/unfollow/", unfollow_user_view, name="unfollow_user"),
    path("<slug:slug>/followers/", followers_list_view, name="followers_list"),
    path("<slug:slug>/following/", following_list_view, name="following_list"),
]
