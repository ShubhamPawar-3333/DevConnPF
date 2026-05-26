from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory, force_authenticate

from explorer.models import Repository, User
from explorer.views import (
    _extract_github_full_name,
    repository_create_view,
    repository_list_or_create_view,
)


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="createuser",
        email="create@example.com",
        password="testpass123",
    )


@pytest.fixture
def api_factory():
    return APIRequestFactory()


def test_extract_github_full_name_accepts_normal_url():
    assert _extract_github_full_name("https://github.com/owner/repo") == "owner/repo"


def test_extract_github_full_name_strips_git_suffix():
    assert _extract_github_full_name("https://github.com/owner/repo.git") == "owner/repo"


def test_extract_github_full_name_rejects_non_github_url():
    assert _extract_github_full_name("https://example.com/owner/repo") is None


@patch("explorer.views.IngestionService")
def test_repository_create_uses_ingestion_service_for_github(
    mock_service_cls, api_factory, user
):
    repo = Repository(
        id=123,
        user=user,
        name="repo",
        source_type="github",
        github_full_name="owner/repo",
        status="cloning",
    )
    mock_service = MagicMock()
    mock_service.ingest_from_github.return_value = repo
    mock_service_cls.return_value = mock_service

    request = api_factory.post(
        "/api/repositories/",
        {"github_url": "https://github.com/owner/repo"},
        format="json",
    )
    force_authenticate(request, user=user)

    response = repository_create_view(request)

    assert response.status_code == 202
    assert response.data == {"repository_id": 123}
    mock_service.ingest_from_github.assert_called_once_with(user, "owner/repo")


def test_repository_list_or_create_returns_empty_list_for_first_time_user(
    api_factory, user
):
    request = api_factory.get("/api/repositories/")
    force_authenticate(request, user=user)

    response = repository_list_or_create_view(request)

    assert response.status_code == 200
    assert response.data == []


@patch("explorer.views.IngestionService")
def test_repository_create_uses_ingestion_service_for_zip(
    mock_service_cls, api_factory, user
):
    repo = Repository(
        id=456,
        user=user,
        name="repo",
        source_type="zip",
        original_filename="repo.zip",
        status="extracting",
    )
    mock_service = MagicMock()
    mock_service.ingest_from_zip.return_value = repo
    mock_service_cls.return_value = mock_service
    zip_file = SimpleUploadedFile("repo.zip", b"PK\x03\x04test", content_type="application/zip")

    request = api_factory.post(
        "/api/repositories/",
        {"zip_file": zip_file},
        format="multipart",
    )
    force_authenticate(request, user=user)

    response = repository_create_view(request)

    assert response.status_code == 202
    assert response.data == {"repository_id": 456}
    mock_service.ingest_from_zip.assert_called_once()
    assert mock_service.ingest_from_zip.call_args.args[0] == user
    assert mock_service.ingest_from_zip.call_args.args[1].name == "repo.zip"
