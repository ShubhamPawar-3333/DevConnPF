# Requirements Document

## Introduction

The Explorer Frontend is a Next.js 14+ (App Router) application providing the client-side interface for the AI Codebase Explorer. It consumes the existing Django REST API to deliver repository browsing, AI-generated summary viewing, natural language search, real-time ingestion progress tracking, and public sharing capabilities. The application is the first module within a Developer Super-App shell, designed for extensibility to future modules.

## Glossary

- **Explorer_Frontend**: The Next.js 14+ client application that serves as the user interface for the AI Codebase Explorer
- **API_Client**: The typed HTTP client layer that wraps all backend API calls with error handling and auth token forwarding
- **Auth_Context**: The React Context provider managing authentication state, login/logout actions, and route protection
- **File_Tree_Browser**: The component rendering the hierarchical repository structure with collapsible directories and summary previews
- **Search_Interface**: The component providing natural language search across AI-generated summaries with debounced input
- **Progress_Tracker**: The component displaying real-time ingestion progress via polling
- **Share_Manager**: The component enabling, disabling, and regenerating public share URLs
- **Public_View**: The read-only repository view accessible without authentication via token-based URLs
- **Auth_Guard**: The route protection component that redirects unauthenticated users to login
- **Tree_Sort_Algorithm**: The function that sorts file tree nodes with directories before files, alphabetically within each group
- **Query_Validator**: The function that validates search queries against length constraints (3-300 characters)
- **Error_Handler**: The centralized function mapping HTTP status codes to user-facing actions
- **TanStack_Query**: The server state management library providing caching, polling, and background refetching
- **Terminal_Status**: A repository status indicating processing is complete: "ready", "partially_summarized", or "failed"

## Requirements

### Requirement 1: Authentication and Session Management

**User Story:** As a developer, I want to authenticate via GitHub OAuth, so that I can securely access my repositories and AI-generated summaries.

#### Acceptance Criteria

1. WHEN a user clicks the login button, THE Explorer_Frontend SHALL redirect the user to the GitHub OAuth authorization page with a CSRF state parameter included in the request
2. WHEN GitHub OAuth returns a successful authorization code, THE Explorer_Frontend SHALL establish a session, store the encrypted access token, and redirect the user to the dashboard within 3 seconds of receiving the callback
3. IF GitHub OAuth returns an error or the user denies authorization, THEN THE Explorer_Frontend SHALL redirect to the /auth/error page and display an error message indicating the reason for failure (e.g., "authorization_denied", "access_denied", or the error description returned by GitHub)
4. WHEN a user clicks the logout button, THE Explorer_Frontend SHALL revoke the GitHub access token, clear the session, and redirect the user to the login page
5. WHILE a user session is active, THE Auth_Context SHALL provide the authenticated user's profile information (username, email, language preference, and avatar URL) to all child components via React Context
6. WHEN the API returns a 401 Unauthorized response during an active session, THE Explorer_Frontend SHALL display a toast notification indicating the session has expired, then redirect the user to the login page within 5 seconds
7. IF a user navigates to a protected route without an active session, THEN THE Explorer_Frontend SHALL redirect the user to the login page
8. WHILE the Auth_Context is verifying the session state on initial load, THE Explorer_Frontend SHALL display a loading skeleton instead of the protected content

### Requirement 2: Route Protection

**User Story:** As a system administrator, I want protected routes to be inaccessible without authentication, so that unauthorized users cannot access private repository data.

#### Acceptance Criteria

1. WHEN an unauthenticated user navigates to a protected route, THE Auth_Guard SHALL store the requested URL and redirect the user to the login page within 1 second
2. WHILE the authentication state is loading, THE Auth_Guard SHALL display a loading skeleton placeholder until the authentication check completes or 10 seconds elapse, whichever comes first
3. IF the authentication check does not complete within 10 seconds, THEN THE Auth_Guard SHALL redirect the user to the login page and display an error message indicating a timeout
4. WHEN an authenticated user navigates to a protected route, THE Auth_Guard SHALL render the requested page content
5. WHEN a user successfully authenticates after being redirected from a protected route, THE Auth_Guard SHALL redirect the user to the originally requested URL instead of the default dashboard

### Requirement 3: Dashboard and Repository Listing

**User Story:** As a developer, I want to see all my ingested repositories on a dashboard, so that I can quickly navigate to any repository.

#### Acceptance Criteria

1. WHEN an authenticated user navigates to the dashboard, THE Explorer_Frontend SHALL display a list of all repositories owned by the user, ordered by ingestion date descending (most recent first)
2. WHEN a repository card is displayed, THE Explorer_Frontend SHALL show the repository name, source type (displayed as "GitHub" or "ZIP Upload"), status (displayed as a human-readable label), file count, and ingestion date
3. WHEN a user clicks a repository card, THE Explorer_Frontend SHALL navigate to that repository's file tree view
4. IF the authenticated user has no repositories, THEN THE Explorer_Frontend SHALL display an empty state message indicating no repositories have been ingested and providing a way to navigate to the ingestion flow
5. IF the dashboard repository list fails to load due to an API error, THEN THE Explorer_Frontend SHALL display an error message indicating the failure and provide a retry action

### Requirement 4: Repository Ingestion

**User Story:** As a developer, I want to ingest new repositories from GitHub or ZIP upload, so that I can generate AI summaries for my codebase.

#### Acceptance Criteria

1. WHEN a user submits a GitHub repository URL or a ZIP file upload for ingestion, THE Explorer_Frontend SHALL send a POST request to the ingestion API, disable the submit control until a response is received, and upon receiving a 202 response with a repository_id, display the progress tracker polling every 5 seconds
2. IF the user has already reached the maximum repository limit of 3, THEN THE Explorer_Frontend SHALL display a message indicating the limit has been reached and list the user's existing repositories each with a delete option
3. IF the ingestion API returns an error, THEN THE Explorer_Frontend SHALL display the error message from the API response and offer a retry option only for network failures or HTTP 5xx responses
4. WHILE the progress tracker is active and the repository status is not "ready", "partially_summarized", or "failed", THE Explorer_Frontend SHALL continue polling the progress endpoint every 5 seconds and display the completed, pending, and failed job counts with a percentage progress bar

### Requirement 5: File Tree Browsing

**User Story:** As a developer, I want to browse my repository's file structure in a hierarchical tree, so that I can navigate to specific files and view their AI summaries.

#### Acceptance Criteria

1. WHEN a user navigates to a repository's tree view, THE File_Tree_Browser SHALL fetch and display the hierarchical file structure from the API, showing a loading skeleton until the response is received
2. THE Tree_Sort_Algorithm SHALL sort directory entries before file entries, with alphabetical ordering (case-insensitive) within each group
3. WHEN a user clicks a directory node, THE File_Tree_Browser SHALL toggle the expanded/collapsed state of that directory, with all directories collapsed by default on initial load
4. WHEN a file node is displayed and its summary status is "completed", THE File_Tree_Browser SHALL show the summary preview truncated to 80 characters (with trailing ellipsis if truncated) alongside the filename; IF the summary status is not "completed", THEN THE File_Tree_Browser SHALL display an empty summary preview
5. WHEN a file node is displayed, THE File_Tree_Browser SHALL show a status indicator reflecting the summary status: completed, pending, failed, permanently_failed, or not_applicable
6. WHEN a user clicks a file node, THE Explorer_Frontend SHALL navigate to the file detail view for that file
7. WHILE a directory is expanded, THE File_Tree_Browser SHALL display its children sorted recursively using the same sort algorithm
8. IF a repository contains more than 200 visible tree nodes, THEN THE File_Tree_Browser SHALL use virtual scrolling so that the initial render and subsequent scroll interactions complete within 100 milliseconds
9. IF the tree API request fails with a 404 status, THEN THE File_Tree_Browser SHALL display a "repository not found" message; IF the request fails with a 403 status, THEN THE File_Tree_Browser SHALL redirect to the login page; IF the request fails with any other error, THEN THE File_Tree_Browser SHALL display an error message with a retry option

### Requirement 6: File Detail View

**User Story:** As a developer, I want to view the AI-generated summary for a specific file and its code blocks, so that I can understand the file's purpose and structure.

#### Acceptance Criteria

1. WHEN a user navigates to a file detail view, THE Explorer_Frontend SHALL display the file path, language, AI summary, and a list of code blocks showing each block's name, kind, and line range
2. WHEN a file has a completed summary, THE Explorer_Frontend SHALL display the full summary text in the user's preferred language
3. IF a file's summary status is "pending", THEN THE Explorer_Frontend SHALL display a placeholder message indicating the summary is being generated
4. IF a file's summary status is "failed" or "permanently_failed", THEN THE Explorer_Frontend SHALL display a message indicating the summary could not be generated
5. WHEN a user clicks a code block in the list, THE Explorer_Frontend SHALL navigate to the block detail view

### Requirement 7: Natural Language Search

**User Story:** As a developer, I want to search across AI summaries using natural language, so that I can find relevant code without knowing exact file paths or function names.

#### Acceptance Criteria

1. WHEN a user types in the search input, THE Search_Interface SHALL debounce the input by 300 milliseconds before executing the search
2. THE Query_Validator SHALL accept search queries with a length between 3 and 300 characters inclusive
3. IF a search query has fewer than 3 characters, THEN THE Search_Interface SHALL display the message "Type at least 3 characters to search"
4. IF a search query exceeds 300 characters, THEN THE Search_Interface SHALL display the message "Query must be 300 characters or less"
5. WHEN search results are returned, THE Search_Interface SHALL display results ordered by descending similarity rank, showing for each result: the file path, the block name (or omitted if the result is a file-level match), and a summary excerpt of up to 200 characters with matching terms wrapped in highlight markup
6. WHEN a user clicks a search result, THE Explorer_Frontend SHALL navigate to the block detail view if the result type is "block", or to the file detail view if the result type is "file"
7. WHEN a search returns zero results, THE Search_Interface SHALL display an empty state with the message "No matches found. Try different keywords."
8. THE Search_Interface SHALL cache search results for 30 seconds per repository and query combination
9. THE Search_Interface SHALL display a maximum of 50 results per search query
10. IF the search API request fails due to a network or server error, THEN THE Search_Interface SHALL display an error message indicating the search could not be completed and SHALL retain the user's current query text in the input field

### Requirement 8: Block Detail View

**User Story:** As a developer, I want to view a code block's source code alongside its AI-generated summary, so that I can understand what the code does.

#### Acceptance Criteria

1. WHEN a user navigates to a block detail view, THE Explorer_Frontend SHALL display the block's name, kind, start line number, end line number, source code, and AI summary in a side-by-side layout with source code on the left and summary on the right
2. WHEN displaying source code, THE Explorer_Frontend SHALL apply syntax highlighting based on the programming language identified in the file's metadata
3. WHEN a block has a parent block, THE Explorer_Frontend SHALL display the parent block name as a clickable link that navigates to the parent block's detail view
4. IF a block's summary status is "pending", THEN THE Explorer_Frontend SHALL display a placeholder message indicating the summary is being generated
5. IF a block's summary status is "failed" or "permanently_failed", THEN THE Explorer_Frontend SHALL display a message indicating the summary could not be generated

### Requirement 9: Multi-Language Support

**User Story:** As a developer, I want to view AI summaries in my preferred language, so that I can understand code explanations in my native language.

#### Acceptance Criteria

1. THE Explorer_Frontend SHALL provide a language selector in settings offering exactly 8 language options: English, Spanish, French, German, Portuguese, Japanese, Korean, and Chinese
2. WHEN a user changes their language preference in settings, THE Explorer_Frontend SHALL send the preference update to the API and display a confirmation indicating the preference was saved successfully
3. IF the language preference update fails, THEN THE Explorer_Frontend SHALL display an error message indicating the preference was not saved and retain the previous language selection in the UI
4. WHEN summaries are displayed, THE Explorer_Frontend SHALL request summaries in the user's configured language preference
5. IF a summary is not available in the user's preferred language, THEN THE Explorer_Frontend SHALL display the English version of the summary with a notice indicating the summary is shown in English because the preferred language is unavailable

### Requirement 10: Real-Time Progress Tracking

**User Story:** As a developer, I want to see real-time progress of repository ingestion and summarization, so that I know how long the process will take and whether it succeeded.

#### Acceptance Criteria

1. WHILE a repository status is not "ready", "partially_summarized", or "failed", THE Progress_Tracker SHALL poll the progress endpoint every 5 seconds
2. WHEN a progress response is received with totalJobs greater than 0, THE Progress_Tracker SHALL display a progress bar with the percentage calculated as Math.round(completed divided by totalJobs multiplied by 100), bounded between 0 and 100 inclusive
3. WHEN a progress response is received with totalJobs equal to 0, THE Progress_Tracker SHALL display a progress bar at 0 percent with an indeterminate state indicator
4. WHEN a progress response is received, THE Progress_Tracker SHALL display numeric counts for completed, pending, and failed jobs
5. WHEN the repository status changes to "ready", "partially_summarized", or "failed", THE Progress_Tracker SHALL stop polling and invoke the onComplete callback within 1 second of receiving the terminal status response
6. IF the progress endpoint returns errors on 3 consecutive polls, THEN THE Progress_Tracker SHALL display a warning banner indicating a connectivity issue while continuing to poll at the same 5-second interval
7. WHEN a successful progress response is received after consecutive errors, THE Progress_Tracker SHALL dismiss the warning banner and reset the consecutive error counter to 0

### Requirement 11: Public Sharing

**User Story:** As a developer, I want to share a read-only view of my repository's AI summaries via a public URL, so that collaborators can browse the summaries without needing an account.

#### Acceptance Criteria

1. WHEN a user enables sharing for a repository, THE Share_Manager SHALL call the sharing API and display the generated public URL in a read-only text input adjacent to a copy button
2. WHEN a user clicks the copy button next to the share URL, THE Share_Manager SHALL copy the URL to the system clipboard and display a confirmation indicator for 3 seconds
3. WHEN a user disables sharing, THE Share_Manager SHALL call the API to revoke the share token, remove the URL display, and the Public_View SHALL return a 404 response for that token within 5 seconds
4. WHEN a user clicks regenerate on the share URL, THE Share_Manager SHALL display a confirmation dialog warning that the previous URL will stop working, and upon confirmation SHALL call the API to create a new token and display the updated URL
5. WHEN a visitor navigates to a valid share URL, THE Public_View SHALL display the repository file tree and summaries in read-only mode without requiring authentication, with no controls for editing, deleting, or managing the repository visible
6. WHEN a visitor navigates to an invalid or expired share token, THE Public_View SHALL display a 404 page with the message "This shared repository is no longer available."
7. THE Public_View SHALL display an attribution banner with the repository owner's username and a "Powered by DevConn" watermark
8. WHEN a visitor enters a search query in the Public_View, THE Public_View SHALL execute a summary search scoped to the shared repository and display results following the same search rules as the authenticated view
9. IF the sharing API call fails when enabling, disabling, or regenerating a share URL, THEN THE Share_Manager SHALL display an error message indicating the operation failed and preserve the previous sharing state

### Requirement 12: API Error Handling

**User Story:** As a developer, I want clear feedback when something goes wrong, so that I can understand the issue and take corrective action.

#### Acceptance Criteria

1. WHEN the API returns a 401 status, THE Error_Handler SHALL redirect the user to the login page and discard any unsaved client-side state for the failed request
2. WHEN the API returns a 403 status, THE Error_Handler SHALL display a toast with the message "You don't have permission for this action" that auto-dismisses after 5 seconds
3. WHEN the API returns a 404 status, THE Error_Handler SHALL display a not-found page
4. WHEN the API returns a 429 status, THE Error_Handler SHALL display a toast with the message "Too many requests. Please wait a moment." that auto-dismisses after 5 seconds
5. WHEN the API returns any other error status, THE Error_Handler SHALL display a toast containing the error message from the response body, or the fallback message "Something went wrong" if the response body contains no message or is unparseable, and the toast SHALL auto-dismiss after 5 seconds
6. WHEN a network request fails, THE TanStack_Query SHALL retry the request up to 3 times with exponential backoff starting at 1 second (1s, 2s, 4s delays) before displaying an error boundary
7. IF all retry attempts for a network request are exhausted, THEN THE TanStack_Query SHALL display an error boundary that shows a message indicating the connection failed and provides a manual "Retry" button to re-trigger the request
8. WHILE a toast notification is displayed, THE Error_Handler SHALL queue any additional toast notifications and display them sequentially, showing no more than 3 toasts on screen simultaneously

### Requirement 13: Super-App Shell Architecture

**User Story:** As a platform architect, I want the frontend to be structured as an extensible super-app shell, so that future modules can be added without architectural changes.

#### Acceptance Criteria

1. THE Explorer_Frontend SHALL use route groups to separate authenticated, public, and auth layouts such that each route group renders a distinct layout component: the (auth) group renders without a navigation sidebar, the (app) group renders with the full shell including sidebar and header, and the (public) group renders with minimal branding only
2. THE Explorer_Frontend SHALL provide a navigation sidebar that renders module entries from a declarative configuration, supporting a minimum of 8 entries without layout overflow, where each entry consists of a label, an icon, and a route path
3. THE Explorer_Frontend SHALL mount shared providers (QueryClient, AuthContext) in the root layout so that any component within any route group can consume them without additional provider wrapping
4. WHEN a new module is added to the super-app, THE Explorer_Frontend SHALL require only a new route group directory and a new entry in the sidebar configuration, with no modifications to existing module code or shared infrastructure files
5. THE Explorer_Frontend SHALL render the navigation sidebar with a visible active-state indicator on the entry corresponding to the current route group

### Requirement 14: Performance and User Experience

**User Story:** As a developer, I want the application to feel fast and responsive, so that browsing repositories and searching summaries is a smooth experience.

#### Acceptance Criteria

1. THE TanStack_Query SHALL serve cached data immediately while refetching in the background using stale-while-revalidate strategy with a default staleTime of 30 seconds for all queries
2. WHEN a user hovers over a file tree node for more than 200 milliseconds, THE Explorer_Frontend SHALL prefetch the file detail data
3. WHILE data is loading, THE Explorer_Frontend SHALL display skeleton placeholders that match the dimensions of the expected content, maintaining a Cumulative Layout Shift score of 0.1 or less
4. THE Explorer_Frontend SHALL use code splitting so each route loads as a separate chunk with a maximum initial bundle size of 200KB gzipped per route
5. WHEN the Explorer_Frontend performs an initial page load, THE Explorer_Frontend SHALL render meaningful content within 1.5 seconds on a standard broadband connection
