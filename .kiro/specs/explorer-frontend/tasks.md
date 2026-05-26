# Implementation Plan: Explorer Frontend

## Overview

Build a Next.js 14+ (App Router) frontend application with TypeScript, Tailwind CSS, and shadcn/ui that serves as the client-side interface for the AI Codebase Explorer. The implementation follows an incremental approach: project scaffolding → shared infrastructure → utility functions → feature components → page wiring → integration.

## Tasks

- [x] 1. Project scaffolding and shared infrastructure
  - [x] 1.1 Initialize Next.js 14+ project with TypeScript, Tailwind CSS, and configure base tooling
    - Create `frontend/` directory with `next.config.ts`, `tsconfig.json` (strict mode), `tailwind.config.ts`, `vitest.config.ts`, `package.json`
    - Install core dependencies: next, react, react-dom, typescript, tailwindcss, @tanstack/react-query, @tanstack/react-virtual, zod, date-fns, lucide-react, class-variance-authority, clsx, tailwind-merge
    - Install dev dependencies: vitest, @testing-library/react, fast-check, msw, @playwright/test
    - Configure `globals.css` with Tailwind directives
    - _Requirements: 13.1, 13.3, 14.4_

  - [x] 1.2 Set up route group layouts and root providers
    - Create `app/layout.tsx` (root layout) mounting QueryClientProvider and AuthContextProvider
    - Create `app/(auth)/layout.tsx` — no sidebar, centered content
    - Create `app/(app)/layout.tsx` — full shell with sidebar and top header
    - Create `app/(public)/layout.tsx` — minimal branding layout
    - _Requirements: 13.1, 13.3_

  - [x] 1.3 Define TypeScript types and API response interfaces
    - Create `lib/types/api.ts` with all interfaces: User, Repository, FileTreeNode, FileDetail, BlockDetail, ProgressReport, SearchResult, ShareInfo, ApiError, LanguageCode, RepositoryStatus, SummaryStatus
    - Create `lib/types/ui-state.ts` with FileTreeState, SearchState, IngestionState
    - _Requirements: 5.4, 7.5, 9.1, 10.2_

  - [x] 1.4 Implement API client layer with typed error handling
    - Create `lib/api/client.ts` with ApiClient class: get, post, put, delete methods
    - Include credentials for session-based auth, JSON parsing, typed ApiError on non-2xx
    - Handle 401 by redirecting to login
    - Create `lib/api/error-handler.ts` with `handleApiError()` function mapping status codes to ErrorAction
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [x] 1.5 Write property test for API error handler totality
    - **Property 4: API Error Handler Totality**
    - Generate random integers (100-599) as status codes, verify handleApiError always returns a valid ErrorAction without throwing
    - Verify 401→redirect, 403→permission toast, 404→not-found, 429→rate-limit toast, others→generic toast
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5**

  - [x] 1.6 Implement Auth Context and Auth Guard
    - Create `lib/auth/auth-context.tsx` with AuthState, AuthActions, login/logout methods
    - Create `lib/auth/auth-guard.tsx` with route protection logic: loading skeleton, redirect on unauthenticated, timeout after 10s
    - _Requirements: 1.5, 1.6, 1.7, 1.8, 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 2. Utility functions and hooks
  - [x] 2.1 Implement tree sort utility
    - Create `lib/utils/tree-sort.ts` with `buildRenderTree()` function
    - Sort directories before files, alphabetical (case-insensitive) within each group
    - Recursively sort expanded directory children
    - _Requirements: 5.2, 5.7_

  - [x] 2.2 Write property test for file tree sort order
    - **Property 1: File Tree Sort Order Consistency**
    - Generate random arrays of FileTreeNode with mixed types, verify directories always precede files and alphabetical order holds recursively
    - **Validates: Requirements 5.2, 5.7**

  - [x] 2.3 Implement search query validation utility
    - Create `lib/utils/validation.ts` with `validateSearchQuery()` function
    - Return `{ valid: true }` for 3-300 chars, `{ valid: false, reason: "too_short" }` for < 3, `{ valid: false, reason: "too_long" }` for > 300
    - _Requirements: 7.2, 7.3, 7.4_

  - [x] 2.4 Write property test for search query validation
    - **Property 2: Search Query Validation Completeness**
    - Generate random strings of varying lengths (0-1000), verify validation returns correct result for all inputs
    - **Validates: Requirements 7.2, 7.3, 7.4**

  - [x] 2.5 Implement summary truncation utility
    - Create `lib/utils/truncate.ts` with truncation function
    - Output ≤ 80 chars; if input > 80 chars, output ends with "…" and is exactly 80 chars
    - _Requirements: 5.4_

  - [x] 2.6 Write property test for summary preview truncation
    - **Property 6: Summary Preview Truncation**
    - Generate random strings of varying lengths, verify output is always ≤ 80 chars and ends with "…" when truncated
    - **Validates: Requirements 5.4**

  - [x] 2.7 Implement progress calculation utility
    - Create `lib/utils/progress.ts` with percentage calculation function
    - Ensure percentage is bounded 0-100 inclusive, handle totalJobs === 0 case
    - _Requirements: 10.2, 10.3_

  - [x] 2.8 Write property test for progress percentage bounds
    - **Property 3: Progress Percentage Bounds**
    - Generate random ProgressReport with valid counts, verify percentage is always 0-100 and completed + pending + failed === totalJobs
    - **Validates: Requirements 10.2**

  - [x] 2.9 Implement TanStack Query hooks
    - Create `lib/hooks/use-debounce.ts` — 300ms debounce hook
    - Create `lib/hooks/use-repository-tree.ts` — fetch file tree
    - Create `lib/hooks/use-file-detail.ts` — fetch file detail with prefetch support
    - Create `lib/hooks/use-block-detail.ts` — fetch block detail
    - Create `lib/hooks/use-repository-progress.ts` — polling with terminal status stop
    - Create `lib/hooks/use-search.ts` — debounced search with validation and 30s cache
    - Create `lib/hooks/use-sharing.ts` — enable/disable/regenerate mutations
    - Create `lib/hooks/use-language-preference.ts` — language update mutation
    - Configure retry (3 attempts, exponential backoff) and staleTime (30s) defaults
    - _Requirements: 7.1, 7.8, 10.1, 10.5, 12.6, 12.7, 14.1_

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Layout and navigation components
  - [x] 4.1 Implement app sidebar and navigation
    - Create `components/layout/app-sidebar.tsx` with declarative nav config supporting 8+ entries
    - Create `components/layout/nav-item.tsx` with active-state indicator based on current route
    - Create `components/layout/top-header.tsx` with user avatar, logout button
    - _Requirements: 13.2, 13.4, 13.5_

  - [x] 4.2 Implement shared UI primitives via shadcn/ui
    - Initialize shadcn/ui and add required components: Button, Input, Card, Progress, Switch, Dialog, Toast, Skeleton, Label, Badge
    - Create `components/ui/` directory with all primitives
    - _Requirements: 14.3_

- [x] 5. Explorer feature components
  - [x] 5.1 Implement File Tree Browser component
    - Create `components/explorer/file-tree/file-tree.tsx` with expand/collapse, selection, virtual scrolling for 200+ nodes
    - Create `components/explorer/file-tree/tree-node.tsx` with status indicators (✓, ⏳, ✗), summary preview, depth indentation
    - Create `components/explorer/file-tree/tree-skeleton.tsx` for loading state
    - Implement hover prefetch (200ms delay) for file detail
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 14.2_

  - [x] 5.2 Write unit tests for File Tree Browser
    - Test rendering with various states (loading, error, empty, populated)
    - Test expand/collapse interactions
    - Test sort order of rendered nodes
    - _Requirements: 5.1, 5.3, 5.6_

  - [x] 5.3 Implement Search Panel component
    - Create `components/explorer/search/search-panel.tsx` with debounced input, validation feedback, results list
    - Create `components/explorer/search/search-result-item.tsx` with highlighted excerpts, file path, block name
    - Display empty state with "No matches found. Try different keywords."
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.9, 7.10_

  - [x] 5.4 Write unit tests for Search Panel
    - Test debounce behavior
    - Test validation message display
    - Test result rendering and navigation
    - _Requirements: 7.1, 7.3, 7.4, 7.7_

  - [x] 5.5 Implement Progress Tracker component
    - Create `components/explorer/progress/progress-panel.tsx` with animated progress bar, counts, status label
    - Create `components/explorer/progress/status-badge.tsx` for human-readable status display
    - Implement consecutive error tracking (3 failures → warning banner)
    - Invoke onComplete callback when terminal status reached
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [x] 5.6 Write unit tests for Progress Tracker
    - Test progress bar percentage calculation
    - Test polling stop on terminal status
    - Test warning banner on consecutive errors
    - _Requirements: 10.2, 10.5, 10.6_

  - [x] 5.7 Implement Share Panel component
    - Create `components/explorer/sharing/share-panel.tsx` with toggle, URL display, copy button, regenerate with confirmation dialog
    - Implement copy-to-clipboard with 3-second confirmation indicator
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.9_

  - [x] 5.8 Implement File Detail and Block Detail components
    - Create `components/explorer/file-detail/file-detail-panel.tsx` with file path, language, summary, block list
    - Create `components/explorer/file-detail/block-list.tsx` with block name, kind, line range
    - Create `components/explorer/block-detail/block-detail-panel.tsx` with side-by-side layout (code left, summary right)
    - Create `components/explorer/block-detail/code-viewer.tsx` with syntax highlighting (lazy loaded)
    - Handle pending/failed summary states with appropriate messages
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 5.9 Implement Dashboard and Repository Card components
    - Create `components/explorer/dashboard/repo-card.tsx` with name, source type, status, file count, ingestion date
    - Create `components/explorer/dashboard/ingest-dialog.tsx` with GitHub URL input and ZIP upload, limit enforcement (max 3)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Page routes and wiring
  - [x] 7.1 Implement auth pages
    - Create `app/(auth)/login/page.tsx` with GitHub OAuth login button (redirect with CSRF state)
    - Create `app/(auth)/auth/error/page.tsx` displaying OAuth error reason
    - _Requirements: 1.1, 1.3_

  - [x] 7.2 Implement dashboard page
    - Create `app/(app)/dashboard/page.tsx` wiring repo list query, repo cards, empty state, error state with retry
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 7.3 Implement repository ingestion page
    - Create `app/(app)/repos/new/page.tsx` wiring ingest dialog, progress tracker, navigation on complete
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 7.4 Implement file tree, file detail, and block detail pages
    - Create `app/(app)/repos/[id]/tree/page.tsx` wiring FileTree with navigation handlers
    - Create `app/(app)/repos/[id]/files/[fileId]/page.tsx` wiring FileDetailPanel
    - Create `app/(app)/repos/[id]/blocks/[blockId]/page.tsx` wiring BlockDetailPanel
    - Create `app/(app)/repos/[id]/page.tsx` redirecting to tree view
    - _Requirements: 5.1, 5.6, 6.1, 6.5, 8.1_

  - [x] 7.5 Implement search page
    - Create `app/(app)/repos/[id]/search/page.tsx` wiring SearchPanel with navigation to file/block detail
    - _Requirements: 7.6_

  - [x] 7.6 Implement settings page
    - Create `app/(app)/settings/page.tsx` with language preference selector (8 options), save confirmation, error handling
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 7.7 Implement public shared view page
    - Create `app/(public)/shared/[token]/page.tsx` with read-only file tree, search, attribution banner, "Powered by DevConn" watermark
    - Handle 404 for invalid/expired tokens with "This shared repository is no longer available."
    - No auth required; no edit/delete/manage controls visible
    - _Requirements: 11.5, 11.6, 11.7, 11.8_

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Error handling, performance, and polish
  - [x] 9.1 Implement toast notification system and error boundaries
    - Wire toast queue (max 3 simultaneous, auto-dismiss 5s) into root layout
    - Create error boundary component for network failure fallback with "Retry" button
    - _Requirements: 12.5, 12.6, 12.7, 12.8_

  - [x] 9.2 Implement OAuth callback handling and session management
    - Wire GitHub OAuth callback to establish session, redirect to dashboard within 3s
    - Implement logout: revoke token, clear session, redirect to login
    - Handle session expiry toast + redirect
    - _Requirements: 1.2, 1.4, 1.6_

  - [x] 9.3 Implement multi-language summary display logic
    - When displaying summaries, request in user's preferred language
    - If preferred language unavailable, show English version with notice
    - _Requirements: 9.4, 9.5_

  - [x] 9.4 Write property test for polling termination guarantee
    - **Property 5: Polling Termination Guarantee**
    - Generate random sequences of ProgressReport ending with terminal status, verify polling stops within one interval
    - **Validates: Requirements 10.1, 10.5**

  - [x] 9.5 Write property test for search excerpt length bound
    - **Property 7: Search Excerpt Length Bound**
    - Generate random SearchResult objects, verify summaryExcerpt is always ≤ 200 characters
    - **Validates: Requirements 7.5**

- [x] 10. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The design uses TypeScript throughout — all implementation uses TypeScript with strict mode
- shadcn/ui components are installed via CLI (`npx shadcn-ui@latest add <component>`)
- TanStack Query v5 is used for all server state; no Redux or Zustand needed
- MSW (Mock Service Worker) is used for component tests to mock API at network level

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["1.4", "1.6", "2.1", "2.3", "2.5", "2.7"] },
    { "id": 3, "tasks": ["1.5", "2.2", "2.4", "2.6", "2.8", "2.9"] },
    { "id": 4, "tasks": ["4.1", "4.2"] },
    { "id": 5, "tasks": ["5.1", "5.3", "5.5", "5.7", "5.8", "5.9"] },
    { "id": 6, "tasks": ["5.2", "5.4", "5.6"] },
    { "id": 7, "tasks": ["7.1", "7.2", "7.3", "7.4", "7.5", "7.6", "7.7"] },
    { "id": 8, "tasks": ["9.1", "9.2", "9.3"] },
    { "id": 9, "tasks": ["9.4", "9.5"] }
  ]
}
```
