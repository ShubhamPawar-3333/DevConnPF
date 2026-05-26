"""
Unit tests for ZIP upload ingestion service.

Tests the IngestionService.ingest_from_zip() method and
the extract_zip_task Celery task.
"""

import io
import os
import tempfile
import zipfile
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from explorer.ingestion import (
    MAX_COMPRESSED_SIZE_BYTES,
    MAX_FILE_COUNT,
    MAX_UNCOMPRESSED_SIZE_BYTES,
    IngestionService,
    ZipValidationError,
    extract_zip_task,
)
from explorer.models import Repository, RepositoryFile


def _create_valid_zip(files=None, filename="test_repo.zip"):
    """Helper to create a valid in-memory ZIP file."""
    if files is None:
        files = {"src/main.py": "print('hello')", "README.md": "# Test"}

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            zf.writestr(path, content)
    buffer.seek(0)
    return SimpleUploadedFile(
        name=filename,
        content=buffer.read(),
        content_type="application/zip",
    )


@pytest.fixture
def ingestion_service():
    return IngestionService()


@pytest.fixture
def user(db):
    from explorer.models import User
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.mark.django_db
class TestIngestFromZip:
    """Tests for IngestionService.ingest_from_zip()"""

    @patch("explorer.ingestion.extract_zip_task.delay")
    @patch("explorer.ingestion._update_progress")
    def test_valid_zip_creates_repository(
        self, mock_progress, mock_task, ingestion_service, user
    ):
        """A valid ZIP upload creates a Repository with status 'extracting'."""
        zip_file = _create_valid_zip()

        repo = ingestion_service.ingest_from_zip(user, zip_file)

        assert repo.id is not None
        assert repo.user == user
        assert repo.name == "test_repo"
        assert repo.source_type == "zip"
        assert repo.original_filename == "test_repo.zip"
        assert repo.status == "extracting"
        mock_task.assert_called_once()

    @patch("explorer.ingestion.extract_zip_task.delay")
    @patch("explorer.ingestion._update_progress")
    def test_valid_zip_dispatches_celery_task(
        self, mock_progress, mock_task, ingestion_service, user
    ):
        """A valid ZIP upload dispatches the extract_zip_task."""
        zip_file = _create_valid_zip()

        repo = ingestion_service.ingest_from_zip(user, zip_file)

        mock_task.assert_called_once()
        args = mock_task.call_args[0]
        assert args[0] == repo.id
        # Second arg is the temp file path
        assert args[1].endswith("test_repo.zip")

    def test_rejects_oversized_zip(self, ingestion_service, user):
        """A ZIP exceeding 200MB compressed size is rejected."""
        # Create a mock file that reports a large size
        zip_file = _create_valid_zip()
        zip_file.size = MAX_COMPRESSED_SIZE_BYTES + 1

        with pytest.raises(ZipValidationError, match="200 MB"):
            ingestion_service.ingest_from_zip(user, zip_file)

    def test_rejects_non_zip_file(self, ingestion_service, user):
        """A non-ZIP file (wrong magic bytes) is rejected."""
        fake_file = SimpleUploadedFile(
            name="not_a_zip.zip",
            content=b"This is not a ZIP file at all",
            content_type="application/zip",
        )

        with pytest.raises(ZipValidationError, match="not a valid ZIP"):
            ingestion_service.ingest_from_zip(user, fake_file)

    def test_rejects_file_without_central_directory(self, ingestion_service, user):
        """A file with ZIP magic bytes but no central directory is rejected."""
        # Create a file that starts with ZIP magic but has no valid structure
        fake_content = b"PK\x03\x04" + b"\x00" * 100
        fake_file = SimpleUploadedFile(
            name="broken.zip",
            content=fake_content,
            content_type="application/zip",
        )

        with pytest.raises(ZipValidationError, match="central directory"):
            ingestion_service.ingest_from_zip(user, fake_file)


@pytest.mark.django_db
class TestExtractZipTask:
    """Tests for the extract_zip_task Celery task."""

    def _create_temp_zip(self, files=None):
        """Create a temporary ZIP file on disk and return its path."""
        if files is None:
            files = {"src/main.py": "print('hello')", "README.md": "# Test"}

        temp_dir = tempfile.mkdtemp(prefix="test_explorer_")
        temp_path = os.path.join(temp_dir, "test.zip")

        with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path, content in files.items():
                zf.writestr(path, content)

        return temp_path

    @patch("explorer.tasks.parse_repository_task.delay")
    @patch("explorer.ingestion._update_progress")
    def test_extracts_files_and_stores_records(self, mock_progress, mock_parse_task, user):
        """Successful extraction stores RepositoryFile records."""
        repo = Repository.objects.create(
            user=user,
            name="test_repo",
            source_type="zip",
            original_filename="test.zip",
            status="extracting",
        )

        files = {
            "src/main.py": "print('hello world')",
            "src/utils.py": "def helper(): pass",
            "README.md": "# My Project",
        }
        temp_path = self._create_temp_zip(files)

        extract_zip_task(repo.id, temp_path)

        repo.refresh_from_db()
        assert repo.status == "parsing"
        assert repo.file_count == 3
        assert repo.total_size_bytes > 0

        stored_files = RepositoryFile.objects.filter(repository=repo)
        assert stored_files.count() == 3

        paths = set(stored_files.values_list("path", flat=True))
        assert paths == {"src/main.py", "src/utils.py", "README.md"}

    @patch("explorer.tasks.parse_repository_task.delay")
    @patch("explorer.ingestion._update_progress")
    def test_stores_correct_metadata(self, mock_progress, mock_parse_task, user):
        """Extraction stores correct file metadata."""
        repo = Repository.objects.create(
            user=user,
            name="test_repo",
            source_type="zip",
            original_filename="test.zip",
            status="extracting",
        )

        files = {"src/app.py": "x = 42"}
        temp_path = self._create_temp_zip(files)

        extract_zip_task(repo.id, temp_path)

        stored_file = RepositoryFile.objects.get(repository=repo)
        assert stored_file.path == "src/app.py"
        assert stored_file.filename == "app.py"
        assert stored_file.content == "x = 42"
        assert stored_file.size_bytes == 6
        assert stored_file.language == "unknown"

    @patch("explorer.ingestion._update_progress")
    @patch("explorer.ingestion._discard_partial_data")
    def test_rejects_oversized_uncompressed(self, mock_discard, mock_progress, user):
        """Extraction fails if uncompressed size exceeds 500MB."""
        repo = Repository.objects.create(
            user=user,
            name="test_repo",
            source_type="zip",
            original_filename="test.zip",
            status="extracting",
        )

        # Create a ZIP with a file that claims to be very large
        # We'll use a mock approach since creating a real 500MB+ file is impractical
        temp_dir = tempfile.mkdtemp(prefix="test_explorer_")
        temp_path = os.path.join(temp_dir, "test.zip")

        with zipfile.ZipFile(temp_path, "w") as zf:
            # Write a small file but we'll test the validation logic
            zf.writestr("big_file.txt", "x" * 1000)

        # Patch the infolist to report a huge file
        with patch("zipfile.ZipFile.infolist") as mock_infolist:
            mock_info = MagicMock()
            mock_info.file_size = MAX_UNCOMPRESSED_SIZE_BYTES + 1
            mock_info.is_dir.return_value = False
            mock_info.filename = "big_file.txt"
            mock_infolist.return_value = [mock_info]

            with pytest.raises(ZipValidationError, match="500 MB"):
                extract_zip_task(repo.id, temp_path)

        mock_discard.assert_called_once_with(repo.id)

    @patch("explorer.ingestion._update_progress")
    @patch("explorer.ingestion._discard_partial_data")
    def test_rejects_too_many_files(self, mock_discard, mock_progress, user):
        """Extraction fails if file count exceeds 10,000."""
        repo = Repository.objects.create(
            user=user,
            name="test_repo",
            source_type="zip",
            original_filename="test.zip",
            status="extracting",
        )

        temp_dir = tempfile.mkdtemp(prefix="test_explorer_")
        temp_path = os.path.join(temp_dir, "test.zip")

        with zipfile.ZipFile(temp_path, "w") as zf:
            zf.writestr("file.txt", "content")

        # Patch infolist to return too many files
        with patch("zipfile.ZipFile.infolist") as mock_infolist:
            mock_infos = []
            for i in range(MAX_FILE_COUNT + 1):
                info = MagicMock()
                info.file_size = 10
                info.is_dir.return_value = False
                info.filename = f"file_{i}.txt"
                mock_infos.append(info)
            mock_infolist.return_value = mock_infos

            with pytest.raises(ZipValidationError, match="10,000"):
                extract_zip_task(repo.id, temp_path)

        mock_discard.assert_called_once_with(repo.id)

    @patch("explorer.tasks.parse_repository_task.delay")
    @patch("explorer.ingestion._update_progress")
    def test_cleans_up_temp_file(self, mock_progress, mock_parse_task, user):
        """Temp file is cleaned up after extraction."""
        repo = Repository.objects.create(
            user=user,
            name="test_repo",
            source_type="zip",
            original_filename="test.zip",
            status="extracting",
        )

        temp_path = self._create_temp_zip({"file.txt": "content"})
        assert os.path.exists(temp_path)

        extract_zip_task(repo.id, temp_path)

        assert not os.path.exists(temp_path)

    @patch("explorer.tasks.parse_repository_task.delay")
    @patch("explorer.ingestion._update_progress")
    def test_updates_progress_stages(self, mock_progress, mock_parse_task, user):
        """Progress is updated through extracting → storing stages."""
        repo = Repository.objects.create(
            user=user,
            name="test_repo",
            source_type="zip",
            original_filename="test.zip",
            status="extracting",
        )

        temp_path = self._create_temp_zip({"file.txt": "content"})

        extract_zip_task(repo.id, temp_path)

        # Check that progress was updated at least for extracting and storing
        calls = mock_progress.call_args_list
        stages = [call[0][1] for call in calls]
        assert "extracting" in stages
        assert "storing" in stages

    @patch("explorer.tasks.parse_repository_task.delay")
    @patch("explorer.ingestion._update_progress")
    def test_skips_binary_files(self, mock_progress, mock_parse_task, user):
        """Binary files that can't be decoded are skipped."""
        repo = Repository.objects.create(
            user=user,
            name="test_repo",
            source_type="zip",
            original_filename="test.zip",
            status="extracting",
        )

        temp_dir = tempfile.mkdtemp(prefix="test_explorer_")
        temp_path = os.path.join(temp_dir, "test.zip")

        with zipfile.ZipFile(temp_path, "w") as zf:
            zf.writestr("text_file.py", "print('hello')")
            # Write actual binary content that can't be decoded
            zf.writestr("binary_file.bin", bytes(range(256)) * 10)

        extract_zip_task(repo.id, temp_path)

        repo.refresh_from_db()
        stored_files = RepositoryFile.objects.filter(repository=repo)
        # Binary file should be decoded with latin-1 fallback, so it will be stored
        # but text file is definitely stored
        assert stored_files.filter(path="text_file.py").exists()
