# Requirements Document

## Introduction

The AI Codebase Explorer is the MVP wedge feature for a unified Developer Super-App. It allows developers to connect a repository (via GitHub OAuth or ZIP upload) and automatically generates plain-language AI summaries for every file and code block. The feature makes any codebase navigable and understandable, solving the universal developer pain point of opening an unfamiliar repository and feeling lost. Summaries are browsable, searchable, and shareable — enabling teams and open-source communities to onboard faster.

## Glossary

- **Explorer**: The AI Codebase Explorer system — the primary application module responsible for repository ingestion, AI summarization, browsing, and search.
- **Repository**: A collection of source code files and directories ingested into the Explorer, either from GitHub or a ZIP upload.
- **File_Summary**: A plain-language AI-generated explanation of a single file's purpose, responsibilities, and key contents.
- **Block_Summary**: A plain-language AI-generated explanation of a discrete code block (function, class, or module-level construct) within a file.
- **File_Tree_Browser**: The UI component that displays the hierarchical directory structure of an ingested repository with associated summaries.
- **Summary_Search**: The search subsystem that indexes AI-generated summaries and allows developers to find code by what it does rather than by filename.
- **Ingestion_Pipeline**: The backend subsystem (Celery-based) responsible for receiving repository data, parsing files, dispatching AI summarization jobs, and storing results.
- **User**: An authenticated developer using the platform.
- **Shared_View**: A publicly accessible, read-only URL that displays an explored repository's file tree and summaries without requiring authentication.
- **Language_Preference**: The user's chosen natural language (e.g., English, Spanish, Japanese) in which AI summaries are generated.

## Requirements

### Requirement 1: GitHub OAuth Authentication

**User Story:** As a developer, I want to sign in with my GitHub account, so that I can authenticate quickly and authorize repository access in one step.

#### Acceptance Criteria

1. WHEN a User initiates sign-in, THE Explorer SHALL redirect the User to the GitHub OAuth authorization flow requesting, at minimum, read access to the User's repositories.
2. WHEN GitHub returns a valid OAuth callback with an authorization code, THE Explorer SHALL exchange the code for an access token within 10 seconds and create or update the User session with a maximum session duration of 7 days of inactivity.
3. IF GitHub returns an OAuth error, the authorization code is invalid or expired, or the User denies authorization, THEN THE Explorer SHALL display an error message indicating the reason for failure and return the User to the sign-in page.
4. WHEN the Explorer receives a valid access token from GitHub, THE Explorer SHALL store the access token in encrypted form at rest and associate it with the User account.
5. WHEN a User signs out, THE Explorer SHALL invalidate the User session, delete the stored GitHub access token, and redirect the User to the landing page.

### Requirement 2: Repository Ingestion via GitHub Connect

**User Story:** As a developer, I want to connect a GitHub repository to the Explorer, so that the platform can analyze and summarize my codebase.

#### Acceptance Criteria

1. WHEN an authenticated User selects a GitHub repository from their accessible repositories list, THE Ingestion_Pipeline SHALL clone the repository contents at the default branch HEAD.
2. WHEN the Ingestion_Pipeline completes cloning, THE Explorer SHALL store the repository metadata (name, owner, branch, commit SHA) and file contents in the database.
3. IF the User's GitHub access token lacks sufficient permissions to read the selected repository, THEN THE Explorer SHALL display an error message indicating which specific permissions are required.
4. IF the repository exceeds 500 MB in total size, THEN THE Explorer SHALL reject the ingestion and inform the User of the size limit.
5. WHILE the Ingestion_Pipeline is cloning a repository, THE Explorer SHALL display a progress indicator to the User showing the current ingestion state.
6. IF the Ingestion_Pipeline fails to clone the repository due to a network error or GitHub API unavailability, THEN THE Explorer SHALL abort the ingestion, display an error message indicating the connectivity failure, and allow the User to retry.
7. IF the clone operation does not complete within 5 minutes, THEN THE Explorer SHALL abort the ingestion, inform the User that the operation timed out, and allow the User to retry.
8. IF a User selects a repository that has already been ingested, THEN THE Explorer SHALL prompt the User to confirm whether to re-ingest the repository, replacing the previously stored data.

### Requirement 3: Repository Ingestion via ZIP Upload

**User Story:** As a developer, I want to upload a ZIP file containing my codebase, so that I can explore repositories not hosted on GitHub.

#### Acceptance Criteria

1. WHEN an authenticated User uploads a valid ZIP file of 200 MB or less in compressed size, THE Ingestion_Pipeline SHALL extract the archive and store the file contents in the database.
2. IF the uploaded file is not a valid ZIP archive, THEN THE Explorer SHALL reject the upload and display an error message indicating the accepted format.
3. IF the extracted ZIP contents exceed 500 MB in total uncompressed size or contain more than 10,000 files, THEN THE Explorer SHALL reject the upload and inform the User of the exceeded limit.
4. IF the uploaded ZIP file exceeds 200 MB in compressed size, THEN THE Explorer SHALL reject the upload and inform the User of the maximum compressed file size.
5. WHILE the Ingestion_Pipeline is processing a ZIP upload, THE Explorer SHALL display a progress indicator showing the current processing stage (uploading, extracting, storing) to the User.
6. WHEN extraction completes successfully, THE Explorer SHALL store the repository metadata (original filename, upload timestamp, file count) in the database.
7. IF the ZIP upload or extraction fails due to a timeout or unexpected error, THEN THE Explorer SHALL discard any partially stored data and display an error message indicating the upload was not completed.

### Requirement 4: AI File-Level Summary Generation

**User Story:** As a developer, I want every file in my repository to have a plain-language summary, so that I can understand what each file does without reading the source code.

#### Acceptance Criteria

1. WHEN the Ingestion_Pipeline finishes storing repository contents, THE Explorer SHALL enqueue an AI summarization job for each file whose extension indicates a recognized programming or markup language (e.g., .py, .js, .ts, .java, .html, .css, .md), excluding binary files, media assets, and auto-generated files (e.g., lock files, minified bundles).
2. WHEN an AI summarization job completes for a file, THE Explorer SHALL store the resulting File_Summary in the database associated with that file.
3. THE Explorer SHALL generate File_Summary content that includes: the file's purpose (what problem it solves or role it plays), a list of its responsibilities (all public functions, classes, or handlers it defines), and its exports or interfaces (all symbols exported or made available to other modules), with the summary length between 50 and 500 words.
4. IF the AI summarization service returns an error for a file, THEN THE Explorer SHALL mark that file as "summary unavailable" and allow the User to retry summarization up to a maximum of 3 retry attempts per file.
5. THE Explorer SHALL generate each File_Summary in the Language_Preference configured by the User at the time of ingestion.
6. WHEN all file summarization jobs for a repository complete, THE Explorer SHALL update the repository status to "Ready" and display an in-app notification informing the User that the repository is ready to browse.

### Requirement 5: AI Code Block-Level Summary Generation

**User Story:** As a developer, I want functions, classes, and module-level constructs to have individual summaries, so that I can understand specific code blocks without reading their implementation.

#### Acceptance Criteria

1. WHEN the Ingestion_Pipeline processes a source code file, THE Explorer SHALL identify discrete code blocks (functions, classes, methods within classes, and module-level constructs) within the file.
2. IF a source code file contains no identifiable code blocks, THEN THE Explorer SHALL skip block-level summarization for that file without reporting an error.
3. WHEN a code block is identified, THE Explorer SHALL enqueue an AI summarization job to generate a Block_Summary for that code block.
4. THE Explorer SHALL generate Block_Summary content that includes the code block's purpose, its parameters or inputs, its return value or side effects, and references to other code blocks it calls or is called by within the same file.
5. THE Explorer SHALL limit each Block_Summary to a maximum of 500 characters.
6. IF the AI summarization service returns an error for a code block, THEN THE Explorer SHALL mark that block as "summary unavailable" and allow the User to retry summarization up to 3 times.
7. THE Explorer SHALL generate each Block_Summary in the Language_Preference configured by the User at the time of ingestion.

### Requirement 6: File Tree Browser with Summaries

**User Story:** As a developer, I want to navigate the repository structure in a file tree and see summaries alongside each file, so that I can quickly orient myself in an unfamiliar codebase.

#### Acceptance Criteria

1. WHEN a User opens an explored repository, THE File_Tree_Browser SHALL display the complete directory hierarchy of the repository with the root-level files and directories visible and all subdirectories in a collapsed state.
2. WHEN a User expands a directory in the File_Tree_Browser, THE File_Tree_Browser SHALL display the contained files and subdirectories sorted alphabetically with directories listed before files.
3. WHEN a User selects a file in the File_Tree_Browser, THE Explorer SHALL display the File_Summary and the list of Block_Summaries for that file.
4. IF a User selects a file whose summary is pending or unavailable, THEN THE Explorer SHALL display the file's current summarization status and provide a retry option for files marked as "summary unavailable".
5. THE File_Tree_Browser SHALL display a truncated preview of each file's File_Summary, limited to 80 characters, next to the filename in the tree view.
6. WHILE file summaries are still being generated for a repository, THE File_Tree_Browser SHALL visually distinguish files with completed summaries from files with pending or failed summaries.
7. WHEN a User selects a code block from the Block_Summary list, THE Explorer SHALL display the source code of that block alongside its Block_Summary.

### Requirement 7: Search Across Summaries

**User Story:** As a developer, I want to search across all AI-generated summaries, so that I can find code by what it does rather than by filename or symbol name.

#### Acceptance Criteria

1. WHEN a User enters a search query, THE Summary_Search SHALL return a maximum of 50 matching File_Summaries and Block_Summaries ranked by textual similarity between the query and the summary content, with the highest-similarity results listed first.
2. THE Summary_Search SHALL accept natural-language queries between 3 and 300 characters in length (e.g., "where is user authentication handled").
3. WHEN search results are displayed, THE Summary_Search SHALL show a highlighted excerpt of the matched summary text (up to 200 characters with the matching portion emphasized), the file path, and the code block name for each result.
4. WHEN a User selects a search result, THE Explorer SHALL navigate to the corresponding file or code block in the File_Tree_Browser.
5. IF no results match the User's query, THEN THE Summary_Search SHALL display a message indicating no matches were found and suggest refining the query.
6. THE Summary_Search SHALL scope results to the currently selected repository.
7. IF a User submits an empty query or a query shorter than 3 characters, THEN THE Summary_Search SHALL display a message indicating the minimum query length requirement without executing a search.

### Requirement 8: Language Preference for Summaries

**User Story:** As a developer, I want to choose the natural language for my AI summaries, so that I can read explanations in my preferred language.

#### Acceptance Criteria

1. THE Explorer SHALL provide a Language_Preference setting in the User's account configuration, defaulting to English when no preference has been explicitly set.
2. WHEN a User sets a Language_Preference, THE Explorer SHALL persist the preference and apply it to all subsequent summarization jobs for that User.
3. WHEN a repository is ingested, THE Explorer SHALL generate all File_Summaries and Block_Summaries in the Language_Preference active at the time of ingestion.
4. THE Explorer SHALL support at minimum: English, Spanish, French, German, Portuguese, Japanese, Korean, and Chinese (Simplified).
5. IF a User changes Language_Preference after a repository has been summarized, THEN THE Explorer SHALL offer the option to regenerate summaries in the new language, replacing the existing summaries upon successful regeneration while keeping the previous-language summaries available for browsing until regeneration completes.

### Requirement 9: Public Sharing of Explored Repositories

**User Story:** As a developer, I want to share a public URL for my explored repository, so that others can browse the AI summaries without needing an account.

#### Acceptance Criteria

1. WHEN a User enables sharing for a repository, THE Explorer SHALL generate a Shared_View URL containing a cryptographically random token of at least 22 URL-safe characters that is unique across all shared repositories.
2. WHEN a visitor accesses a valid Shared_View URL, THE Explorer SHALL display the File_Tree_Browser with all File_Summaries and Block_Summaries in read-only mode without requiring authentication, and SHALL enable the Summary_Search scoped to that repository.
3. WHEN a User disables sharing for a repository, THE Explorer SHALL invalidate the Shared_View URL within 5 seconds and return a 404 response for all subsequent access attempts.
4. WHEN a User regenerates the Shared_View URL, THE Explorer SHALL create a new unique URL and immediately invalidate the previous URL so that it returns a 404 response.
5. THE Shared_View SHALL display an attribution banner indicating the repository owner's username.
6. IF a visitor accesses a Shared_View URL for a repository that has been deleted, THEN THE Explorer SHALL return a 404 response.
7. IF a visitor accesses a Shared_View URL that does not match any existing shared repository, THEN THE Explorer SHALL return a 404 response.

### Requirement 10: Summarization Job Status and Progress

**User Story:** As a developer, I want to see the progress of AI summarization for my repository, so that I know when the analysis is complete and can identify any failures.

#### Acceptance Criteria

1. WHILE the Ingestion_Pipeline is processing summarization jobs for a repository, THE Explorer SHALL display the count of completed, pending, and failed summarization jobs, updating the displayed counts within 10 seconds of any job state change.
2. WHEN all summarization jobs for a repository complete successfully, THE Explorer SHALL update the repository status to "Ready".
3. IF one or more summarization jobs fail and at least one job has completed successfully, THEN THE Explorer SHALL update the repository status to "Partially Summarized" and list each failed file or block by name.
4. IF all summarization jobs for a repository fail, THEN THE Explorer SHALL update the repository status to "Failed" and list each failed file or block by name.
5. WHEN a User requests retry for failed summarization jobs, THE Explorer SHALL re-enqueue those specific jobs without re-processing successful summaries, up to a maximum of 3 retry attempts per job.
6. IF a summarization job has exhausted its maximum retry attempts, THEN THE Explorer SHALL mark that job as permanently failed and exclude it from further retry requests.
7. THE Explorer SHALL allow the User to browse already-completed summaries while remaining jobs are still in progress.
