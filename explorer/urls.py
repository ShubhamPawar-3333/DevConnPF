"""
URL configuration for the explorer app.
"""

from django.urls import path

from explorer import views

app_name = "explorer"

urlpatterns = [
    # Authentication (API - used by frontend)
    path("auth/me/", views.current_user_view, name="current_user"),
    path("auth/login/", views.login_view, name="login"),
    path("auth/github/", views.login_view, name="login_github"),  # alias for frontend
    path("auth/github/url/", views.github_auth_url_view, name="github_auth_url"),
    path("auth/logout/", views.api_logout_view, name="api_logout"),
    path("auth/github/callback/", views.github_callback_api_view, name="github_callback_api"),
    path("auth/error/", views.oauth_callback_view, name="oauth_error"),
    # Language preference
    path("auth/language/", views.language_preference_view, name="language_preference"),
    path("users/me/language/", views.language_preference_view, name="language_preference_alt"),
    # Repositories (list, create, delete)
    path("repositories/", views.repository_list_or_create_view, name="repository_list"),
    path("repositories/<int:repository_id>/", views.repository_delete_view, name="repository_delete"),
    # Progress tracking
    path(
        "repositories/<int:repository_id>/progress/",
        views.repository_progress_view,
        name="repository_progress",
    ),
    # File tree browser
    path(
        "repositories/<int:repository_id>/tree/",
        views.repository_tree_view,
        name="repository_tree",
    ),
    # File detail
    path(
        "repositories/<int:repository_id>/files/<int:file_id>/",
        views.file_detail_view,
        name="file_detail",
    ),
    # Block detail
    path(
        "repositories/<int:repository_id>/blocks/<int:block_id>/",
        views.block_detail_view,
        name="block_detail",
    ),
    # Summary regeneration
    path(
        "repositories/<int:repository_id>/regenerate-summaries/",
        views.regenerate_summaries_view,
        name="regenerate_summaries",
    ),
    # Search
    path(
        "repositories/<int:repository_id>/search/",
        views.repository_search_view,
        name="repository_search",
    ),
    # Sharing management (authenticated)
    path(
        "repositories/<int:repository_id>/share/",
        views.repository_share_view,
        name="repository_share",
    ),
    path(
        "repositories/<int:repository_id>/share/regenerate/",
        views.repository_share_regenerate_view,
        name="repository_share_regenerate",
    ),
    # Public shared view (no auth required)
    path(
        "shared/<str:token>/",
        views.shared_repository_view,
        name="shared_repository",
    ),
]
