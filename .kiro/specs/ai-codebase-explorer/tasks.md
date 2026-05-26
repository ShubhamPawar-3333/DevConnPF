# Implementation Plan: AI Codebase Explorer

## Overview

This plan implements the AI Codebase Explorer as a Django application with PostgreSQL, Celery/Redis for async processing, tree-sitter for code parsing, and OpenAI GPT-4o-mini for summary generation. Tasks are ordered to build foundational models and services first, then layer on features incrementally, wiring everything together at the end.

## Tasks

- [x] 1. Set up project structure, dependencies, and core models
  - [x] 1.1 Create the `explorer` Django app and install dependencies
    - Create the `explorer` app within the Django project
    - Add dependencies to `requirements.txt`: `celery`, `redis`, `django-celery-results`, `social-auth-app-django`, `cryptography` (for Fernet encryption), `tree-sitter`, `tree-sitter-language-pack`, `openai`, `hypothesis` (dev), `pytest-django` (dev)
    - Configure Celery in `settings.py` and create `celery.py` app config
    - Configure `social-auth-app-django` with GitHub backend in settings
    - Set up Redis as Celery broker and result backend
    - _Requirements: 1.1, 2.1, 4.1, 5.1_

  - [x] 1.2 Define core database models and migrations
    - Create custom User model extending `AbstractUser` with `language_preference` (CharField, default "en") and `github_token_encrypted` (BinaryField, nullable)
    - Create `Repository` model with all fields (user FK, name, source_type, github_full_name, branch, commit_sha, original_filename, status, file_count, total_size_bytes, timestamps)
    - Create `RepositoryFile` model with unique constraint on `(repository, path)`
    - Create `FileSummary` model with OneToOne to RepositoryFile, GIN index on `summary_text` tsvector
    - Create `CodeBlock` model with FK to RepositoryFile
    - Create `BlockSummary` model with OneToOne to CodeBlock, GIN index on `summary_text` tsvector
    - Create `SharedView` model with unique token field
    - Create `SummarizationJob` model with composite index on `(repository, status)`
    - Run `makemigrations` and `migrate`
    - _Requirements: 1.4, 2.2, 3.6, 4.2, 5.1, 9.1, 10.1_

  - [ ]* 1.3 Write property tests for model validators
    - **Property 3: Ingestion Size and Count Validation** — test that the validator accepts iff compressed ≤ 200MB AND uncompressed ≤ 500MB AND file_count ≤ 10,000
    - **Validates: Requirements 2.4, 3.3, 3.4**
    - **Property 6: Summary Length Constraints** — test that file summary validator accepts iff 50 ≤ word_count ≤ 500, and block summary validator accepts iff char_count ≤ 500
    - **Validates: Requirements 4.3, 5.5**

- [x] 2. Implement authentication module
  - [x] 2.1 Implement GitHub OAuth flow and token encryption
    - Create `explorer/auth_services.py` with `GitHubOAuthService` class: `initiate_oauth()`, `handle_callback()`, `revoke_token()`
    - Create `explorer/encryption.py` with `TokenEncryptionService` class using Fernet symmetric encryption: `encrypt(token)` → bytes, `decrypt(encrypted)` → str
    - Configure `social-auth-app-django` pipeline to store encrypted token on User model after successful OAuth
    - Create Django views: `login_view` (redirects to GitHub OAuth), `oauth_callback_view` (handles code exchange), `logout_view` (invalidates session, deletes token, redirects to landing)
    - Set session expiry to 7 days of inactivity
    - Handle OAuth errors (denied, invalid code, expired) with appropriate error messages and redirect to sign-in
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 2.2 Write property test for token encryption round-trip
    - **Property 1: Token Encryption Round-Trip** — for any valid token string, encrypt then decrypt produces the original
    - **Validates: Requirements 1.4**

  - [ ]* 2.3 Write unit tests for OAuth flow
    - Test redirect URL construction with correct scopes
    - Test callback handling with valid code
    - Test error handling for denied/invalid/expired codes
    - Test session invalidation and token deletion on logout
    - _Requirements: 1.1, 1.2, 1.3, 1.5_

- [x] 3. Implement repository ingestion module
  - [x] 3.1 Implement GitHub repository ingestion service and Celery task
    - Create `explorer/ingestion.py` with `IngestionService` class
    - Implement `ingest_from_github(user, repo_full_name)`: validate user token permissions, check repo size (reject > 500MB), create Repository record with status "cloning", dispatch `clone_repository_task`
    - Implement `clone_repository_task` Celery task: use GitHub API to fetch repo contents at default branch HEAD, store files in `RepositoryFile` records, update Repository metadata (branch, commit_sha, file_count, total_size_bytes), handle re-ingestion (prompt user, replace existing data)
    - Implement 5-minute timeout for clone operations
    - Handle network errors and GitHub API unavailability with abort + retry option
    - Update progress in Redis during cloning
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_

  - [x] 3.2 Implement ZIP upload ingestion service and Celery task
    - Implement `ingest_from_zip(user, zip_file)` in `IngestionService`: validate ZIP format (magic bytes + central directory), validate compressed size ≤ 200MB, create Repository record with status "extracting", dispatch `extract_zip_task`
    - Implement `extract_zip_task` Celery task: extract archive, validate uncompressed size ≤ 500MB and file count ≤ 10,000, store files in `RepositoryFile` records, store metadata (original_filename, upload timestamp, file_count)
    - Discard partial data on failure (timeout or unexpected error)
    - Update progress in Redis (uploading → extracting → storing)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [ ]* 3.3 Write property tests for ingestion validation
    - **Property 4: ZIP Format Validation** — for any byte sequence, validator returns valid=True iff it's a structurally valid ZIP archive
    - **Validates: Requirements 3.2**
    - **Property 2: Repository Metadata Preservation** — storing and retrieving metadata returns all fields unchanged
    - **Validates: Requirements 2.2, 3.6**

  - [ ]* 3.4 Write unit tests for ingestion error handling
    - Test size limit rejection (> 500MB repo, > 200MB ZIP, > 500MB uncompressed, > 10,000 files)
    - Test invalid ZIP format rejection
    - Test timeout handling (5-minute clone timeout)
    - Test network error handling and retry option
    - Test re-ingestion confirmation flow
    - _Requirements: 2.3, 2.4, 2.6, 2.7, 2.8, 3.2, 3.3, 3.4, 3.7_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement code parsing module
  - [x] 5.1 Implement tree-sitter code parser
    - Create `explorer/parsing.py` with `CodeParser` class
    - Implement `detect_language(filename)`: map file extensions to tree-sitter language grammars (support Python, JavaScript, TypeScript, Java, Go, Rust, C, C++, Ruby, PHP, HTML, CSS, Markdown, and more)
    - Implement `is_summarizable_file(filename)`: return True for recognized programming/markup extensions, False for binary files, media assets, lock files, minified bundles, and auto-generated files
    - Implement `parse_file(content, language)`: use tree-sitter to parse AST and extract functions, classes, methods, and module-level constructs as `CodeBlock` dataclass instances with name, kind, start_line, end_line, content, parent_block
    - Store extracted `CodeBlock` records in the database after parsing
    - _Requirements: 4.1, 5.1, 5.2_

  - [ ]* 5.2 Write property tests for code parsing
    - **Property 5: File Summarizability Classification** — for any filename, `is_summarizable_file()` returns True iff extension is in recognized set AND filename doesn't match auto-generated patterns
    - **Validates: Requirements 4.1**
    - **Property 9: Code Block Parsing Validity** — for any valid source code, parser returns blocks with non-empty name, valid kind, start_line < end_line, start_line ≥ 1, and content is substring of original
    - **Validates: Requirements 5.1**

- [x] 6. Implement AI summarization module
  - [x] 6.1 Implement summarization service and Celery tasks
    - Create `explorer/summarization.py` with `SummarizationService` class
    - Implement `summarize_file(file, language)`: construct prompt for GPT-4o-mini requesting file purpose, responsibilities, exports/interfaces in the specified language; validate response is 50–500 words; store `FileSummary`
    - Implement `summarize_block(block, file_context, language)`: construct prompt requesting block purpose, parameters, return value, side effects, references in specified language; validate response ≤ 500 chars; store `BlockSummary`
    - Implement `summarize_file_task` Celery task with `max_retries=3` and exponential backoff (30s base for rate limits, 15s base for timeouts)
    - Implement `summarize_block_task` Celery task with same retry strategy
    - Create `SummarizationJob` records to track each job's state
    - On ingestion completion, enqueue summarization jobs for all summarizable files and their code blocks
    - Mark files/blocks as "summary unavailable" on permanent failure (3 retries exhausted)
    - Implement `retry_failed(repository_id)`: re-enqueue failed jobs (not permanently_failed, not completed)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [ ]* 6.2 Write property tests for summarization logic
    - **Property 7: Retry Logic Invariants** — retry_count never exceeds 3, permanently_failed jobs excluded from retries, completed jobs never re-enqueued
    - **Validates: Requirements 4.4, 5.6, 10.5, 10.6**

  - [ ]* 6.3 Write unit tests for summarization service
    - Test prompt construction includes correct language
    - Test summary length validation (reject < 50 words or > 500 words for files, > 500 chars for blocks)
    - Test retry with exponential backoff on rate limit and timeout errors
    - Test permanent failure marking after 3 retries
    - _Requirements: 4.3, 4.4, 4.5, 5.5, 5.6, 5.7_

- [x] 7. Implement progress tracking module
  - [x] 7.1 Implement progress service and API endpoint
    - Create `explorer/progress.py` with `ProgressService` class
    - Implement `get_progress(repository_id)`: query `SummarizationJob` table to compute completed, pending, failed counts; derive repository status
    - Implement `update_job_state(job_id, state)`: update job status and increment counters in Redis for fast polling
    - Create DRF API endpoint `GET /api/repositories/{id}/progress/` returning `{total, completed, pending, failed, status}`
    - Implement status derivation logic: "ready" if all completed, "failed" if all failed, "partially_summarized" if mixed with none pending, "summarizing" if any pending/in_progress
    - Update repository status field when all jobs complete
    - Send in-app notification when repository status transitions to "Ready"
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 4.6_

  - [ ]* 7.2 Write property test for status derivation
    - **Property 8: Repository Status Derivation** — for any set of job states, derived status matches the specification rules, and completed + pending + failed = total
    - **Validates: Requirements 4.6, 10.1, 10.2, 10.3, 10.4**

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement file tree browser API
  - [x] 9.1 Implement file tree and file detail API endpoints
    - Create `explorer/views.py` (or extend) with DRF viewsets
    - Implement `GET /api/repositories/{id}/tree/` endpoint: return complete directory hierarchy with root-level items visible, subdirectories collapsed, directories sorted before files (alphabetical, case-insensitive), include truncated File_Summary preview (80 chars) next to each file
    - Implement `GET /api/repositories/{id}/files/{file_id}/` endpoint: return full File_Summary and list of Block_Summaries for the selected file
    - Implement `GET /api/repositories/{id}/blocks/{block_id}/` endpoint: return source code alongside Block_Summary
    - Visually distinguish files by summary status (completed, pending, failed) in response data
    - Include retry option in response for files marked "summary unavailable"
    - Allow browsing completed summaries while others are still pending
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 10.7_

  - [ ]* 9.2 Write property test for directory sort order
    - **Property 10: Directory Sort Order** — for any list of entries, sort produces directories before files, each group alphabetical case-insensitive
    - **Validates: Requirements 6.2**

  - [ ]* 9.3 Write unit tests for file tree API
    - Test collapsed initial state
    - Test directory expansion with correct sort order
    - Test summary preview truncation at 80 characters
    - Test pending/unavailable file status display
    - _Requirements: 6.1, 6.2, 6.5, 6.6_

- [x] 10. Implement search module
  - [x] 10.1 Implement full-text search service and API endpoint
    - Create `explorer/search.py` with `SummarySearchService` class
    - Implement `search(repository_id, query, limit=50)`: use PostgreSQL full-text search with `ts_rank` for ranking, query both `FileSummary` and `BlockSummary` tsvector indexes, return results ordered by decreasing similarity
    - Create DRF API endpoint `GET /api/repositories/{id}/search/?q=<query>` returning max 50 results with: highlighted excerpt (200 chars with match emphasized), file_path, block_name, result_type
    - Validate query length (3–300 characters), return error message for invalid queries
    - Scope all results to the specified repository (no cross-repository leakage)
    - Return "no matches found" message with suggestion to refine query when results are empty
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [ ]* 10.2 Write property tests for search
    - **Property 11: Search Result Ordering, Limit, and Isolation** — results ≤ 50, all belong to queried repo, ordered by decreasing rank
    - **Validates: Requirements 7.1, 7.6**
    - **Property 12: Search Query Validation** — validator accepts iff 3 ≤ length ≤ 300
    - **Validates: Requirements 7.2**

  - [ ]* 10.3 Write unit tests for search
    - Test natural language query returns relevant results
    - Test empty results message
    - Test query length validation (too short, too long)
    - Test result navigation to file/block
    - _Requirements: 7.1, 7.2, 7.5, 7.4_

- [x] 11. Implement language preference module
  - [x] 11.1 Implement language preference settings and regeneration
    - Add language preference API endpoint `PUT /api/users/me/language/` accepting supported language codes: en, es, fr, de, pt, ja, ko, zh
    - Default to "en" when no preference set
    - Persist preference on User model
    - Pass language preference to all summarization tasks at ingestion time
    - Implement regeneration endpoint `POST /api/repositories/{id}/regenerate-summaries/`: re-enqueue all summarization jobs with new language, keep previous summaries available until regeneration completes, then replace
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 12. Implement public sharing module
  - [x] 12.1 Implement sharing service and shared view endpoints
    - Create `explorer/sharing.py` with `SharingService` class
    - Implement `enable_sharing(repository)`: generate cryptographically random URL-safe token (≥ 22 chars), create `SharedView` record, return share URL
    - Implement `disable_sharing(repository)`: set `is_active=False` on SharedView, ensure 404 within 5 seconds
    - Implement `regenerate_url(repository)`: create new token, invalidate old immediately
    - Create public endpoint `GET /shared/{token}/` (no auth required): display File_Tree_Browser + summaries in read-only mode with Summary_Search enabled, show attribution banner with owner username
    - Return 404 for invalid tokens, inactive shares, and deleted repositories
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

  - [ ]* 12.2 Write property test for share token format
    - **Property 13: Share Token Format and Uniqueness** — token ≥ 22 chars, URL-safe characters only, all generated tokens are distinct
    - **Validates: Requirements 9.1**

  - [ ]* 12.3 Write unit tests for sharing
    - Test token generation format and length
    - Test 404 for invalid/inactive/deleted tokens
    - Test disable invalidates within 5 seconds
    - Test regenerate creates new token and invalidates old
    - Test attribution banner displays owner username
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

- [x] 13. Implement MVP hard caps and usage tracking
  - [x] 13.1 Enforce repository limits and add usage tracking
    - Enforce 3 repositories per user limit: reject ingestion with clear error message when limit reached
    - Enforce 200 files per repository limit: during ingestion, only process first 200 summarizable files, inform user of the cap
    - Add usage tracking fields or model to record: repos created, files processed, summaries generated per user
    - Add branding watermark to shared views (e.g., "Powered by [App Name]" in shared view footer)
    - _Requirements: 2.4, 3.3 (MVP caps layered on top)_

- [x] 14. Wire together ingestion → parsing → summarization pipeline
  - [x] 14.1 Integrate the full pipeline end-to-end
    - After `clone_repository_task` or `extract_zip_task` completes successfully, trigger code parsing for all stored files
    - After parsing completes, enqueue summarization jobs for all summarizable files and extracted code blocks
    - Ensure progress tracking updates at each stage transition (cloning → parsing → summarizing → ready)
    - Wire repository status updates through the pipeline
    - Ensure partial browsing works (users can browse completed summaries while others process)
    - _Requirements: 2.1, 2.2, 3.1, 4.1, 4.6, 5.1, 10.1, 10.7_

  - [ ]* 14.2 Write integration tests for the full pipeline
    - Test GitHub ingestion → parsing → summarization with mocked GitHub API and OpenAI
    - Test ZIP upload → parsing → summarization with mocked OpenAI
    - Test progress updates through each stage
    - Test partial failure handling (some summaries fail, repo becomes "partially_summarized")
    - _Requirements: 2.1, 3.1, 4.1, 4.6, 10.1, 10.2, 10.3, 10.4_

- [x] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The stack is Django + PostgreSQL + Celery/Redis + tree-sitter + OpenAI GPT-4o-mini
- MVP hard caps: 3 repos per user, 200 files per repo, branding watermark on shared views
- Hypothesis is used for property-based testing with minimum 100 examples per property

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["1.3", "2.1"] },
    { "id": 3, "tasks": ["2.2", "2.3", "3.1", "3.2"] },
    { "id": 4, "tasks": ["3.3", "3.4", "5.1"] },
    { "id": 5, "tasks": ["5.2", "6.1"] },
    { "id": 6, "tasks": ["6.2", "6.3", "7.1"] },
    { "id": 7, "tasks": ["7.2", "9.1"] },
    { "id": 8, "tasks": ["9.2", "9.3", "10.1", "11.1", "12.1"] },
    { "id": 9, "tasks": ["10.2", "10.3", "12.2", "12.3", "13.1"] },
    { "id": 10, "tasks": ["14.1"] },
    { "id": 11, "tasks": ["14.2"] }
  ]
}
```
