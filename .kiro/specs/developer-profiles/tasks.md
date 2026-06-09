# Implementation Plan: Developer Profiles with Project Pages

## Overview

This implementation plan breaks down the Developer Profiles feature into discrete, executable coding tasks. The feature adds a LinkedIn-style identity layer to the Developer Super-App, integrating with the existing AI Codebase Explorer. The implementation creates a new Django app `profiles` with RESTful API endpoints, and builds corresponding Next.js frontend pages and components.

**Key Integration Points:**
- Extends existing `explorer.User` model with one-to-one Profile relationship
- Links to existing `explorer.Repository` model for project showcase
- Reuses existing GitHub OAuth and `CorsSessionAuthentication`
- Follows existing project patterns for DRF views, serializers, and React Query hooks

**Architecture:**
- Backend: Django app `profiles` with models, serializers, services, views, and URL routing
- Frontend: Next.js pages under `app/(app)/profile/` and `app/(app)/onboarding/`, React components, API client hooks
- Testing: Property-based tests (Hypothesis) for 21 correctness properties + unit tests for edge cases

---

## Tasks

### 1. Backend Foundation: Django App Setup and Core Models

- [x] 1.1 Create profiles Django app and register in settings
  - Create `profiles/` directory with `__init__.py`, `apps.py`, `admin.py`, `urls.py`
  - Add `'profiles'` to `INSTALLED_APPS` in `devconnpf/settings.py`
  - Include `profiles.urls` under `/api/profiles/` in `devconnpf/urls.py`
  - _Requirements: All backend requirements depend on app registration_

- [x] 1.2 Implement Profile model with validation
  - Create `profiles/models.py` with `Profile` model
  - Fields: `user` (OneToOne to User), `slug` (unique, validated), `display_name`, `avatar_url`, `bio`, `location`, `website_url`, `github_username`, `skill_tags` (JSONField), `follower_count`, `following_count`, `status`, `github_sync_status`, `created_at`, `updated_at`
  - Add database indexes on `slug` and `status`
  - Add model-level constraints for slug format using RegexValidator and MinLengthValidator
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.3, 2.4, 3.1, 3.3, 9.1, 9.3_

- [x] 1.3 Implement ProjectEntry model
  - Add `ProjectEntry` model to `profiles/models.py`
  - Fields: `profile` (FK to Profile), `repository` (FK to explorer.Repository), `custom_description`, `display_order`, `added_at`
  - Add unique constraint on (`profile`, `repository`)
  - Add ordering by `display_order`, `-added_at`
  - Add database index on (`profile`, `display_order`)
  - _Requirements: 5.1, 5.2, 5.5, 5.6, 5.7, 5.9_


- [x] 1.4 Implement Follow model
  - Add `Follow` model to `profiles/models.py`
  - Fields: `follower` (FK to Profile), `target` (FK to Profile), `created_at`
  - Add unique constraint on (`follower`, `target`)
  - Add CheckConstraint for no self-follow: `~Q(follower=F('target'))`
  - Add indexes on (`follower`, `-created_at`) and (`target`, `-created_at`)
  - _Requirements: 6.1, 6.2, 6.3, 6.8, 6.9_

- [x] 1.5 Create and run database migrations
  - Run `python manage.py makemigrations profiles`
  - Run `python manage.py migrate`
  - Verify all three models created with correct schema
  - _Requirements: All model-dependent requirements_

### 2. Backend Business Logic: Services Layer

- [x] 2.1 Implement ProfileService for slug validation
  - Create `profiles/services.py` with `ProfileService` class
  - Define `RESERVED_SLUGS` frozenset containing: "admin", "api", "auth", "settings", "dashboard", "login", "explore", "shared", "repos", "search"
  - Define `SLUG_PATTERN` regex: `^[a-z][a-z0-9\-]{2,39}$`
  - Implement `validate_slug(slug, exclude_profile_id)` method that checks format, reserved words, and uniqueness
  - Implement `is_slug_available(slug, exclude_profile_id)` method
  - Raise Django ValidationError with specific messages for each violation type
  - _Requirements: 1.3, 1.4, 3.5, 3.8, 9.2, 9.3, 9.4, 9.5, 9.6_

- [x] 2.2 Implement GitHubImportService for optional profile import
  - Add `GitHubImportService` class to `profiles/services.py`
  - Define `GITHUB_USER_URL = "https://api.github.com/user"`
  - Define `TIMEOUT_SECONDS = 10`
  - Implement `fetch_github_profile(user)` method that:
    - Decrypts stored GitHub token from `user.github_token_encrypted`
    - Makes GET request to GitHub API with 10-second timeout
    - Returns dict with `avatar_url`, `name`, `bio` (omitting null/empty values)
    - Raises `GitHubTokenMissingError` if no token stored
    - Raises `GitHubImportError` on API failure (timeout, 401, 403, 5xx)
  - _Requirements: 4.1, 4.2, 4.4, 4.5, 4.6, 4.7_

- [x] 2.3 Implement FollowService for follow management
  - Add `FollowService` class to `profiles/services.py`
  - Implement `follow(follower, target)` method:
    - Create Follow record using `get_or_create` for idempotence
    - Raise ValidationError if follower == target (self-follow)
    - Increment follower/following counts on success
    - Return created Follow object
  - Implement `unfollow(follower, target)` method:
    - Delete Follow record
    - Decrement follower/following counts
    - Raise Follow.DoesNotExist if relationship doesn't exist
  - Implement `sync_counts(profile)` method to recalculate follower/following counts from actual Follow records
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6, 6.7_


### 3. Backend API: Serializers

- [x] 3.1 Implement ProfilePublicSerializer
  - Create `profiles/serializers.py` with `ProfilePublicSerializer(ModelSerializer)`
  - Fields: `slug`, `display_name`, `avatar_url`, `bio`, `location`, `website_url`, `skill_tags`, `follower_count`, `following_count`, `projects` (SerializerMethodField), `joined_date` (from created_at), `github_username`
  - Implement `get_projects()` method to return list of ProjectEntry objects with nested repository data
  - Configure `skill_tags` as ListField of strings
  - Allow null for all optional fields (avatar_url, bio, location, website_url, github_username)
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 2.7, 8.1, 8.2, 8.4_

- [x] 3.2 Implement ProfileOwnerSerializer extending ProfilePublicSerializer
  - Add `email` field (source='user.email', read_only=True)
  - Add `github_sync_status` field
  - Extend Meta.fields to include private owner-only fields
  - _Requirements: 8.2, 8.3_

- [x] 3.3 Implement ProjectEntrySerializer
  - Create `ProjectEntrySerializer(ModelSerializer)` in `profiles/serializers.py`
  - Fields: `id`, `repository_name` (from repository.name), `custom_description`, `primary_language` (from repository.language), `explorer_link` (SerializerMethodField), `display_order`, `added_at`
  - Implement `get_explorer_link()` to generate URL to AI Codebase Explorer
  - _Requirements: 5.2, 5.3_

- [x] 3.4 Implement FollowSerializer for follower/following lists
  - Create `FollowSerializer(ModelSerializer)` in `profiles/serializers.py`
  - For followers list: serialize `follower` profile with slug, display_name, avatar_url, bio
  - For following list: serialize `target` profile with same fields
  - Include `created_at` timestamp
  - _Requirements: 6.8, 6.9_

### 4. Backend API: Profile CRUD Views

- [x] 4.1 Implement profile creation endpoint
  - Create `profiles/views.py` with `create_profile_view` function
  - Endpoint: `POST /api/profiles/me/`
  - Permissions: IsAuthenticated
  - Validates and creates Profile for authenticated user
  - Returns 201 with ProfileOwnerSerializer on success
  - Returns 400 if profile already exists or validation fails
  - _Requirements: 1.1, 1.2, 1.6_

- [x] 4.2 Implement profile retrieval endpoint
  - Add `get_profile_view` function to `profiles/views.py`
  - Endpoint: `GET /api/profiles/<slug>/`
  - Permissions: AllowAny (public access)
  - Returns ProfilePublicSerializer for visitors
  - Returns ProfileOwnerSerializer if authenticated user is profile owner
  - Returns 404 if slug doesn't exist or profile status is not 'active'
  - _Requirements: 2.1, 2.2, 2.5, 8.2, 8.3, 8.6_

- [x] 4.3 Implement profile update endpoint
  - Add `update_profile_view` function to `profiles/views.py`
  - Endpoint: `PUT /api/profiles/<slug>/update/` and `PATCH /api/profiles/<slug>/update/`
  - Permissions: IsAuthenticated + owner check
  - Validates all field updates using ProfileService for slug validation
  - Returns 403 if non-owner attempts update
  - Returns 400 with field errors on validation failure, leaves profile unchanged
  - Returns 200 with updated ProfileOwnerSerializer on success
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_


### 5. Backend API: GitHub Import Views

- [x] 5.1 Implement GitHub import preview endpoint
  - Add `github_import_preview_view` function to `profiles/views.py`
  - Endpoint: `GET /api/profiles/me/github/preview/`
  - Permissions: IsAuthenticated
  - Calls GitHubImportService.fetch_github_profile()
  - Returns current profile values alongside fetched GitHub values for comparison
  - Returns 400 with error if no token or token invalid
  - Returns 500 if GitHub API timeout or failure
  - _Requirements: 4.1, 4.2, 4.4, 4.5, 4.6_

- [x] 5.2 Implement GitHub import apply endpoint
  - Add `github_import_apply_view` function to `profiles/views.py`
  - Endpoint: `POST /api/profiles/me/github/apply/`
  - Permissions: IsAuthenticated
  - Request body: `{"fields": ["avatar_url", "display_name", "bio"]}` (subset of fields to apply)
  - Updates only selected fields on profile
  - Applies same validation as profile update
  - Returns 200 with updated ProfileOwnerSerializer
  - Returns 400 if validation fails, leaves profile unchanged
  - _Requirements: 4.3, 4.7_

### 6. Backend API: Project Management Views

- [x] 6.1 Implement add project endpoint
  - Add `add_project_view` function to `profiles/views.py`
  - Endpoint: `POST /api/profiles/me/projects/`
  - Permissions: IsAuthenticated
  - Request body: `{"repository_id": int, "custom_description": string}`
  - Validates user owns the repository
  - Validates profile doesn't already have 50 projects
  - Validates repository not already linked to profile
  - Creates ProjectEntry with next display_order
  - Returns 201 with ProjectEntrySerializer
  - _Requirements: 5.1, 5.4, 5.7, 5.8, 5.9, 5.10_

- [x] 6.2 Implement remove project endpoint
  - Add `remove_project_view` function to `profiles/views.py`
  - Endpoint: `DELETE /api/profiles/me/projects/<project_id>/`
  - Permissions: IsAuthenticated + owner check
  - Validates project belongs to authenticated user's profile
  - Deletes ProjectEntry (doesn't affect underlying Repository)
  - Returns 204 No Content on success
  - Returns 404 if project doesn't exist or doesn't belong to user
  - _Requirements: 5.5_

- [x] 6.3 Implement reorder projects endpoint
  - Add `reorder_projects_view` function to `profiles/views.py`
  - Endpoint: `PUT /api/profiles/me/projects/reorder/`
  - Permissions: IsAuthenticated
  - Request body: `{"projects": [{"id": int, "display_order": int}, ...]}`
  - Bulk updates display_order for multiple ProjectEntry records
  - Validates all project IDs belong to authenticated user's profile
  - Returns 200 with updated project list
  - _Requirements: 5.6_


### 7. Backend API: Follow Management Views

- [x] 7.1 Implement follow user endpoint
  - Add `follow_user_view` function to `profiles/views.py`
  - Endpoint: `POST /api/profiles/<slug>/follow/`
  - Permissions: IsAuthenticated
  - Calls FollowService.follow() with authenticated user's profile and target profile
  - Returns 201 with created Follow relationship
  - Returns 400 if attempting self-follow
  - Returns 404 if target profile doesn't exist
  - Returns existing relationship if already following (idempotent)
  - _Requirements: 6.1, 6.3, 6.4, 6.5, 6.7_

- [x] 7.2 Implement unfollow user endpoint
  - Add `unfollow_user_view` function to `profiles/views.py`
  - Endpoint: `DELETE /api/profiles/<slug>/unfollow/`
  - Permissions: IsAuthenticated
  - Calls FollowService.unfollow() with authenticated user's profile and target profile
  - Returns 204 No Content on success
  - Returns 404 if target profile doesn't exist or no follow relationship exists
  - _Requirements: 6.2, 6.6, 6.7_

- [x] 7.3 Implement followers list endpoint
  - Add `followers_list_view` function to `profiles/views.py`
  - Endpoint: `GET /api/profiles/<slug>/followers/?page=1`
  - Permissions: AllowAny
  - Returns paginated list of profiles that follow the target profile
  - Page size: default 20, max 100 (via query param `page_size`)
  - Ordered by follow date descending
  - Returns 404 if target profile doesn't exist
  - _Requirements: 6.8_

- [x] 7.4 Implement following list endpoint
  - Add `following_list_view` function to `profiles/views.py`
  - Endpoint: `GET /api/profiles/<slug>/following/?page=1`
  - Permissions: AllowAny
  - Returns paginated list of profiles that the target profile follows
  - Page size: default 20, max 100 (via query param `page_size`)
  - Ordered by follow date descending
  - Returns 404 if target profile doesn't exist
  - _Requirements: 6.9_

### 8. Backend API: Search and Discovery

- [x] 8.1 Implement profile search endpoint
  - Add `search_profiles_view` function to `profiles/views.py`
  - Endpoint: `GET /api/profiles/search/?q=<query>&skill_tag=<tag>&page=1`
  - Permissions: AllowAny
  - Query validation: 1-200 characters
  - Search fields: display_name, username, bio, skill_tags (case-insensitive substring match)
  - Filter by skill_tag if provided
  - Filter to active profiles only
  - Returns paginated results (20 per page)
  - Rank display_name/username matches above bio/skill matches
  - Returns 400 if query empty or exceeds 200 characters
  - Returns empty list if no matches
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_


### 9. Backend API: URL Routing and Permissions

- [x] 9.1 Implement custom DRF permissions
  - Create `profiles/permissions.py` with `IsProfileOwner` permission class
  - Checks `request.user.profile == obj` for profile update/delete operations
  - Create `IsProjectOwner` permission class
  - Checks `request.user.profile == obj.profile` for project operations
  - _Requirements: 3.2_

- [x] 9.2 Wire up all URL routes
  - Complete `profiles/urls.py` with all endpoint routes:
    - `me/` → create_or_get_my_profile_view
    - `me/github/preview/` → github_import_preview_view
    - `me/github/apply/` → github_import_apply_view
    - `me/projects/` → add_project_view
    - `me/projects/<int:project_id>/` → remove_project_view
    - `me/projects/reorder/` → reorder_projects_view
    - `search/` → search_profiles_view
    - `<slug:slug>/` → get_profile_view
    - `<slug:slug>/update/` → update_profile_view
    - `<slug:slug>/follow/` → follow_user_view
    - `<slug:slug>/unfollow/` → unfollow_user_view
    - `<slug:slug>/followers/` → followers_list_view
    - `<slug:slug>/following/` → following_list_view
  - Register all routes with proper names for reverse lookup
  - _Requirements: 9.1, 9.2_

- [x] 9.3 Register Profile, ProjectEntry, Follow models in Django admin
  - Create `profiles/admin.py` with ModelAdmin classes for each model
  - Configure list_display, search_fields, list_filter for easy debugging
  - Add inline for ProjectEntry in Profile admin
  - _Requirements: Backend debugging and development_

### 10. Backend Testing: Property-Based Tests (Part 1)

- [x]* 10.1 Set up property test infrastructure
  - Create `profiles/tests/` directory with `__init__.py`
  - Create `profiles/tests/test_properties.py`
  - Install and configure Hypothesis testing library
  - Create shared test fixtures: test user, test profile factory, test repository factory
  - _Requirements: All property tests_

- [x]* 10.2 Property 1: Slug Format Validation
  - **Property 1: Slug Format Validation**
  - **Validates: Requirements 1.3, 1.4, 3.5, 9.3, 9.4, 9.6**
  - Generate random strings with various violations (wrong length, invalid chars, uppercase, starts with digit, reserved words)
  - Verify validation accepts valid slugs and rejects invalid ones with specific error messages
  - Test 100+ iterations

- [x]* 10.3 Property 2: Slug Uniqueness and Immediate Release
  - **Property 2: Slug Uniqueness and Immediate Release**
  - **Validates: Requirements 1.3, 9.2**
  - Generate two valid slugs A and B
  - Create profile with slug A, verify accessible
  - Change slug from A to B
  - Verify slug A returns 404 and slug B returns profile
  - Test 100+ iterations


- [x]* 10.4 Property 3: Profile Serialization Completeness and Optional Field Nullability
  - **Property 3: Profile Serialization Completeness and Optional Field Nullability**
  - **Validates: Requirements 8.1, 8.4**
  - Generate profiles with all combinations of optional fields set/unset
  - Serialize for public visitor
  - Verify all required top-level keys present
  - Verify unset optional fields serialize as `null` (not omitted)
  - Test 100+ iterations

- [x]* 10.5 Property 4: Owner vs. Visitor Serialization Difference
  - **Property 4: Owner vs. Visitor Serialization Difference**
  - **Validates: Requirements 8.2, 8.3**
  - Generate profile with owner, anonymous visitor, and other authenticated user
  - Verify owner serialization includes `email` and `github_sync_status`
  - Verify visitor serialization excludes those fields
  - Test 100+ iterations

- [x]* 10.6 Property 5: Serialization Round Trip
  - **Property 5: Serialization Round Trip**
  - **Validates: Requirements 8.5**
  - Generate valid profile with random field values
  - Serialize to JSON, then deserialize
  - Verify all field values identical before and after
  - Test 100+ iterations

- [x]* 10.7 Property 6: Project Entry Display Order Preservation
  - **Property 6: Project Entry Display Order Preservation**
  - **Validates: Requirements 2.7, 5.6**
  - Generate profile with multiple projects with shuffled display_order values
  - Serialize profile
  - Verify projects list sorted ascending by display_order
  - Test 100+ iterations

- [x]* 10.8 Property 7: Project Entry Count Constraint
  - **Property 7: Project Entry Count Constraint**
  - **Validates: Requirements 5.4, 5.8**
  - Generate profile with 0 to 51 projects
  - Verify can add projects until count reaches 50
  - Verify 51st addition rejected with error
  - Verify removing a project at limit allows adding one more
  - Test 100+ iterations

### 11. Backend Testing: Property-Based Tests (Part 2)

- [x]* 11.1 Property 8: Duplicate Project Entry Rejection
  - **Property 8: Duplicate Project Entry Rejection**
  - **Validates: Requirements 5.9**
  - Generate profile with existing project entry
  - Attempt to add same repository again
  - Verify rejected with error and project list unchanged
  - Test 100+ iterations

- [x]* 11.2 Property 9: Profile Immutability on Invalid Input
  - **Property 9: Profile Immutability on Invalid Input**
  - **Validates: Requirements 3.4, 3.7, 3.8**
  - Generate profile with valid existing data
  - Submit invalid update (oversized bio, invalid slug, oversized avatar, etc.)
  - Verify returns 400 error
  - Verify profile data unchanged after failed update
  - Test 100+ iterations

- [x]* 11.3 Property 10: Non-Owner Update Rejection
  - **Property 10: Non-Owner Update Rejection**
  - **Validates: Requirements 3.2**
  - Generate profile and another authenticated user who is not owner
  - Attempt update as non-owner
  - Verify rejected with 403 and profile unchanged
  - Test 100+ iterations


- [x]* 11.4 Property 11: Follow Count Consistency Invariant
  - **Property 11: Follow Count Consistency Invariant**
  - **Validates: Requirements 6.7**
  - Generate random sequence of follow/unfollow operations on multiple profiles
  - After each operation, verify follower_count equals actual Follow record count (where profile is target)
  - Verify following_count equals actual Follow record count (where profile is follower)
  - Test 100+ iterations with varying operation sequences

- [x]* 11.5 Property 12: Follow Idempotence
  - **Property 12: Follow Idempotence**
  - **Validates: Requirements 6.4**
  - Generate two profiles where A already follows B
  - Attempt follow operation again
  - Verify returns existing relationship without creating duplicate
  - Verify total Follow record count unchanged
  - Test 100+ iterations

- [x]* 11.6 Property 13: Self-Follow Rejection
  - **Property 13: Self-Follow Rejection**
  - **Validates: Requirements 6.3**
  - Generate any profile
  - Attempt to follow itself
  - Verify rejected with validation error
  - Verify no Follow record created
  - Test 100+ iterations

- [x]* 11.7 Property 14: Follow/Unfollow Round Trip
  - **Property 14: Follow/Unfollow Round Trip**
  - **Validates: Requirements 6.1, 6.2, 6.7**
  - Generate two distinct profiles A and B
  - Record initial follower/following counts
  - A follows B
  - A unfollows B
  - Verify Follow relationship no longer exists
  - Verify both profiles' counts restored to initial values
  - Test 100+ iterations

- [x]* 11.8 Property 15: Paginated Follow Lists Ordering
  - **Property 15: Paginated Follow Lists Ordering**
  - **Validates: Requirements 6.8, 6.9**
  - Generate profile with N followers (varying N from 0 to 200)
  - Request followers list with different page sizes (default 20, max 100)
  - Verify results ordered by follow creation date descending
  - Verify every follow relationship appears exactly once across all pages
  - Verify no duplicates or omissions
  - Test 100+ iterations

### 12. Backend Testing: Property-Based Tests (Part 3)

- [x]* 12.1 Property 16: Search Inclusivity and Active-Only Invariant
  - **Property 16: Search Inclusivity and Active-Only Invariant**
  - **Validates: Requirements 7.1, 7.4**
  - Generate set of active and inactive profiles with varying content
  - Generate random search query (1-200 chars)
  - Verify results contain all active profiles where query matches display_name, username, bio, or skill_tags (case-insensitive)
  - Verify results contain NO inactive profiles regardless of match
  - Test 100+ iterations

- [x]* 12.2 Property 17: Skill Tag Filter Correctness
  - **Property 17: Skill Tag Filter Correctness**
  - **Validates: Requirements 7.3**
  - Generate profiles with various skill_tags
  - Apply skill_tag filter T
  - Verify all returned profiles contain T in their skill_tags
  - Verify no returned profile lacks T
  - Test 100+ iterations


- [x]* 12.3 Property 18: GitHub Import Selective Field Application
  - **Property 18: GitHub Import Selective Field Application**
  - **Validates: Requirements 4.3**
  - Generate profile with existing values for avatar_url, display_name, bio
  - Mock GitHub API response with different values
  - Generate random non-empty subset S of {avatar_url, display_name, bio}
  - Apply import with selected fields S
  - Verify exactly fields in S updated with GitHub values
  - Verify fields not in S remain unchanged
  - Test 100+ iterations

- [x]* 12.4 Property 19: GitHub Import Null Field Omission
  - **Property 19: GitHub Import Null Field Omission**
  - **Validates: Requirements 4.7**
  - Generate profile with existing values
  - Mock GitHub API response with random subset of fields null/empty
  - Request preview
  - Verify preview omits null/empty fields
  - Apply import
  - Verify profile fields corresponding to null GitHub values remain unchanged
  - Test 100+ iterations

- [x]* 12.5 Property 20: GitHub Import Failure Preserves Profile
  - **Property 20: GitHub Import Failure Preserves Profile**
  - **Validates: Requirements 4.4**
  - Generate profile with existing values
  - Mock various GitHub API failures (timeout, 401, 403, 500, 503)
  - Attempt import
  - Verify returns error response
  - Verify profile data identical before and after failed attempt
  - Test 100+ iterations

- [x]* 12.6 Property 21: Skill Tags Serialized Without Truncation
  - **Property 21: Skill Tags Serialized Without Truncation**
  - **Validates: Requirements 2.3**
  - Generate profile with 0 to 20 skill tags
  - Serialize profile
  - Verify skill_tags array contains exactly all tags with no modification, truncation, or ordering change
  - Test 100+ iterations

### 13. Backend Testing: Unit Tests and Edge Cases

- [x]* 13.1 Create unit test file for models
  - Create `profiles/tests/test_models.py`
  - Test Profile model constraints:
    - Slug uniqueness enforced at database level
    - OneToOne relationship with User enforced
    - Default values (status='active', follower_count=0, skill_tags=[])
  - Test ProjectEntry unique constraint on (profile, repository)
  - Test Follow CheckConstraint prevents self-follow at database level
  - _Requirements: 1.3, 5.9, 6.3_

- [x]* 13.2 Create unit test file for services
  - Create `profiles/tests/test_services.py`
  - Test ProfileService edge cases:
    - Reserved slug rejection
    - Slug format validation messages
    - Slug uniqueness with exclude_profile_id
  - Test GitHubImportService error handling:
    - Missing token raises GitHubTokenMissingError
    - Timeout raises GitHubImportError
    - 401/403/500 responses raise GitHubImportError
  - Test FollowService:
    - get_or_create behavior for idempotence
    - Count sync correctness
  - _Requirements: 1.4, 4.4, 4.5, 4.6, 6.4, 6.7_


- [x]* 13.3 Create integration test file for API views
  - Create `profiles/tests/test_views.py`
  - Test smoke cases: URL routing, anonymous profile access returns 200, inactive slug returns 404
  - Test profile creation edge cases: missing required fields, existing profile rejection
  - Test non-existent slug returns 404
  - Test search with no matches returns empty list with total=0
  - Test reserved slug list contains required entries
  - Test unfollow when not following returns 404
  - _Requirements: 1.1, 1.5, 2.2, 2.5, 6.6, 7.6, 9.1_

- [x]* 13.4 Create unit tests for GitHub import with mocked API
  - Create `profiles/tests/test_github_import.py`
  - Mock GitHub API responses using unittest.mock
  - Test preview returns current value alongside GitHub value
  - Test user without GitHub token receives appropriate error
  - Test GitHub 401 response generates re-authenticate prompt
  - Test stored encrypted token used for API call (decrypt and use)
  - _Requirements: 4.1, 4.2, 4.5, 4.6_

- [x] 13.5 Backend checkpoint
  - Run `python manage.py test profiles` and ensure all tests pass
  - Ensure all migrations applied cleanly
  - Ask the user if questions arise before proceeding to frontend.

### 14. Frontend Infrastructure: API Client and Types

- [x] 14.1 Create TypeScript type definitions for profiles
  - Create `frontend/lib/types/profiles.ts`
  - Define interfaces: `Profile`, `ProfileOwner` (extends Profile with email, github_sync_status), `ProjectEntry`, `Follow`, `FollowList`
  - Define request types: `ProfileCreateData`, `ProfileUpdateData`, `ProjectAddData`, `ProjectReorderData`
  - Define response types: `PaginatedResponse<T>`, `SearchResponse<T>`
  - Follow existing typing patterns from the project
  - _Requirements: All frontend requirements_

- [x] 14.2 Create profiles API client module
  - Create `frontend/lib/api/profiles.ts`
  - Implement `profilesApi` object with all endpoints following existing `apiClient` patterns in the project
  - Methods: `getProfile`, `getMyProfile`, `createProfile`, `updateProfile`
  - Methods: `previewGitHubImport`, `applyGitHubImport`
  - Methods: `addProject`, `removeProject`, `reorderProjects`
  - Methods: `followUser`, `unfollowUser`, `getFollowers`, `getFollowing`
  - Methods: `searchProfiles`
  - Use existing authentication headers and CSRF token patterns from the project
  - _Requirements: All API communication requirements_


- [x] 14.3 Create React Query hooks for profiles
  - Create `frontend/lib/hooks/useProfiles.ts`
  - Implement hooks following existing patterns from the project:
    - `useProfile(slug)` - fetch profile by slug
    - `useMyProfile()` - fetch authenticated user's profile
    - `useCreateProfile()` - mutation for profile creation
    - `useUpdateProfile(slug)` - mutation for profile updates
  - Implement GitHub import hooks:
    - `useGitHubImportPreview()` - fetch GitHub data for review
    - `useApplyGitHubImport()` - mutation to apply imported data
  - Configure proper cache invalidation on mutations
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 4.2, 4.3_

- [x] 14.4 Create React Query hooks for projects and follows
  - Add to `frontend/lib/hooks/useProfiles.ts`:
    - `useAddProject()` - mutation to add project
    - `useRemoveProject()` - mutation to remove project
    - `useReorderProjects()` - mutation to reorder projects
    - `useFollow(slug)` - mutation to follow user
    - `useUnfollow(slug)` - mutation to unfollow user
    - `useFollowers(slug, page)` - fetch followers list with pagination
    - `useFollowing(slug, page)` - fetch following list with pagination
    - `useSearchProfiles(query, skillTag, page)` - search with filters and pagination
  - Configure proper cache invalidation and optimistic updates where appropriate
  - _Requirements: 5.1, 5.5, 5.6, 6.1, 6.2, 6.8, 6.9, 7.1, 7.2, 7.3_

### 15. Frontend Pages: Onboarding Flow

- [x] 15.1 Create onboarding page
  - Create `frontend/app/(app)/onboarding/page.tsx`
  - Implement multi-step onboarding form:
    - Step 1: Display name (required, 2-100 chars) and slug (required, validated)
    - Step 2: Bio (optional, max 500 chars) and location (optional, max 100 chars)
    - Step 3: Avatar upload or URL (optional) and skill tags (optional, max 20)
    - Optional: GitHub import button (skip to manual entry)
  - Show real-time slug validation feedback (available/taken, format errors)
  - Use `useCreateProfile` mutation hook
  - Redirect to profile edit page or dashboard on completion
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 15.2 Add onboarding redirect logic
  - Update authenticated layout in `frontend/app/(app)/layout.tsx`
  - Check if user has profile using `useMyProfile` hook
  - Redirect to `/onboarding` if no profile exists and user is not already on onboarding page
  - _Requirements: 1.5_

### 16. Frontend Pages: Profile View

- [x] 16.1 Create public profile page
  - Create `frontend/app/(app)/[slug]/page.tsx`
  - Fetch profile using `useProfile(slug)` hook
  - Render ProfileHeader component with avatar, display name, bio, location, website link
  - Render ProfileStats component with follower/following counts
  - Render SkillTagList component with skill badges
  - Render ProjectShowcase component with project cards
  - Show follow/unfollow button if authenticated and not own profile
  - Handle 404 if slug doesn't exist
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_


- [x] 16.2 Create profile components library
  - Create `frontend/components/profile/ProfileHeader.tsx`
    - Display avatar (with fallback to default), display name, slug, bio
    - Show location and website if set
    - Show follow/unfollow button for other users' profiles
  - Create `frontend/components/profile/ProfileStats.tsx`
    - Display follower count (clickable to see list)
    - Display following count (clickable to see list)
  - Create `frontend/components/profile/SkillTagList.tsx`
    - Render skill tags as styled badges
    - Handle empty state (no tags)
  - Follow existing component patterns and styling from the project
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6_

- [x] 16.3 Create project showcase components
  - Create `frontend/components/profile/ProjectShowcase.tsx`
    - Container component that lists ProjectCard components
    - Handle empty state (no projects)
  - Create `frontend/components/profile/ProjectCard.tsx`
    - Display project name, custom description, primary language badge
    - Include "Explore Code" link to AI Codebase Explorer
    - Link format: `/repos/${repository.id}`
  - _Requirements: 5.2, 5.3_

### 17. Frontend Pages: Profile Editing

- [x] 17.1 Create profile edit page
  - Create `frontend/app/(app)/profile/edit/page.tsx`
  - Only accessible to profile owner (redirect to profile view if not owner)
  - Fetch profile using `useMyProfile` hook
  - Render ProfileEditForm component with pre-filled current values
  - Use `useUpdateProfile` mutation hook
  - Show success/error toast messages on update
  - _Requirements: 3.1, 3.2, 3.4_

- [x] 17.2 Create profile edit form components
  - Create `frontend/components/profile/ProfileEditForm.tsx`
    - Form sections: BasicInfo (display name, slug, bio, location, website), Avatar, SkillTags
    - Real-time validation for slug format and availability
    - Field validation: display_name (2-100), bio (max 500), location (max 100), website (URL format)
    - Skill tag editor: add/remove tags (max 20, each max 50 chars)
    - Show validation errors inline
    - Submit button with loading state
  - Create `frontend/components/profile/AvatarUpload.tsx`
    - Avatar preview with current image
    - Upload button (accept PNG/JPEG/WebP, max 2MB)
    - Option to enter URL instead
    - Validation error display
  - _Requirements: 3.1, 3.3, 3.5, 3.6, 3.7, 3.8_

- [x] 17.3 Add GitHub import UI to profile edit form
  - Create `frontend/components/profile/GitHubImportButton.tsx`
    - Button to trigger GitHub import preview
    - Use `useGitHubImportPreview` hook
  - Create `frontend/components/profile/GitHubImportDialog.tsx`
    - Modal showing current profile values vs. GitHub values side by side
    - Checkboxes to select which fields to import (avatar_url, display_name, bio)
    - Apply button using `useApplyGitHubImport` mutation
    - Error handling for missing/expired token with re-auth prompt
  - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6, 4.7_


### 18. Frontend Pages: Project Management

- [x] 18.1 Create project management page
  - Create `frontend/app/(app)/profile/projects/page.tsx`
  - Only accessible to profile owner
  - Fetch profile using `useMyProfile` hook
  - Render ProjectManagementPanel component
  - Show current project count and 50-project limit
  - _Requirements: 5.1, 5.4, 5.5, 5.6, 5.8_

- [x] 18.2 Create project management components
  - Create `frontend/components/profile/ProjectManagementPanel.tsx`
    - Display list of current projects with drag-to-reorder functionality
    - Remove button for each project (with confirmation)
    - Add project button that opens repository selector
    - Project limit indicator (X/50 projects)
    - Use `useRemoveProject` and `useReorderProjects` mutation hooks
  - Create `frontend/components/profile/AddProjectDialog.tsx`
    - Modal with dropdown/search of user's repositories
    - Custom description input (optional, max 300 chars)
    - Add button using `useAddProject` mutation
    - Show error if repository already added or limit reached
  - Install and configure `@dnd-kit/core` or similar for drag-and-drop reordering
  - _Requirements: 5.1, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10_

### 19. Frontend Pages: Follow Lists and Networking

- [x] 19.1 Create followers list page
  - Create `frontend/app/(app)/[slug]/followers/page.tsx`
  - Use `useFollowers(slug, page)` hook with pagination
  - Display list of follower profiles with avatar, display name, bio snippet
  - Link each profile to their profile page
  - Pagination controls (previous/next, page numbers)
  - Show empty state if no followers
  - _Requirements: 6.8_

- [x] 19.2 Create following list page
  - Create `frontend/app/(app)/[slug]/following/page.tsx`
  - Use `useFollowing(slug, page)` hook with pagination
  - Display list of following profiles with avatar, display name, bio snippet
  - Link each profile to their profile page
  - Pagination controls (previous/next, page numbers)
  - Show empty state if not following anyone
  - _Requirements: 6.9_

- [x] 19.3 Add follow/unfollow interactions
  - Create `frontend/components/profile/FollowButton.tsx`
    - Show "Follow" or "Following" state based on current relationship
    - Use `useFollow` and `useUnfollow` mutation hooks
    - Optimistic updates for immediate UI feedback
    - Handle self-follow rejection (hide button on own profile)
    - Show error toast if operation fails
  - Integrate FollowButton into ProfileHeader component
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

### 20. Frontend Pages: Search and Discovery

- [x] 20.1 Create profile search page
  - Create `frontend/app/(app)/search/page.tsx`
  - Search input with debounced query (validates 1-200 chars)
  - Skill tag filter dropdown (optional)
  - Use `useSearchProfiles(query, skillTag, page)` hook
  - Display search results as list of profile cards
  - Pagination controls
  - Show empty state if no results
  - Show validation error if query invalid
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_


- [x] 20.2 Create search result components
  - Create `frontend/components/profile/SearchResultCard.tsx`
    - Compact profile card with avatar, display name, bio snippet, skill tags
    - Link to full profile page
    - Show match highlighting (optional enhancement)
  - Create `frontend/components/profile/SkillTagFilter.tsx`
    - Dropdown or autocomplete for skill tag selection
    - Fetches available skill tags from profiles (optional: add backend endpoint for tag list)
    - Clear filter button
  - _Requirements: 7.2, 7.3_

### 21. Frontend Testing and Polish

- [x]* 21.1 Create component tests for profile components
  - Create test files using Vitest + React Testing Library following existing patterns in the project
  - Test `ProfileHeader.tsx`: renders all fields, handles missing optional fields, shows follow button conditionally
  - Test `SkillTagList.tsx`: renders tags, handles empty state
  - Test `ProjectCard.tsx`: renders project data, explorer link correct format
  - Test `ProfileEditForm.tsx`: validation works, submit calls mutation
  - Mock API responses using `vi.mock()` or MSW
  - _Requirements: All UI rendering requirements_

- [x]* 21.2 Create page-level tests
  - Test onboarding flow: steps render, validation works, successful submission redirects
  - Test profile view page: fetches profile, renders components, 404 for non-existent slug
  - Test profile edit page: owner access only, pre-fills form, updates work
  - Test search page: query validation, results display, pagination works
  - _Requirements: 1.1, 1.5, 2.5, 3.2, 7.5_

- [x] 21.3 Add navigation integration
  - Update main navigation in `frontend/components/layout/` or `frontend/app/(app)/layout.tsx`
  - Add link to authenticated user's profile (if profile exists)
  - Add link to search/discovery page
  - Add profile dropdown menu with: "My Profile", "Edit Profile", "Settings", "Logout"
  - _Requirements: Navigation UX_

- [x] 21.4 Final frontend checkpoint
  - Run `npm run build` to ensure no TypeScript errors
  - Run `npm run test` to ensure all tests pass
  - Manually test key flows: onboarding, view profile, edit profile, add project, follow/unfollow, search
  - Ask the user if questions arise.

### 22. Integration and End-to-End Testing

- [x] 22.1 Create end-to-end test scenarios (manual or automated)
  - Test full onboarding flow from first login to profile creation
  - Test profile → project → explorer navigation flow
  - Test GitHub import with real GitHub account (dev environment only)
  - Test follow/unfollow with multiple users
  - Test search finds profiles correctly
  - Test edge cases: 50 project limit, slug conflicts, missing data
  - _Requirements: All integration requirements_

- [x] 22.2 Test authentication integration
  - Verify GitHub OAuth flow still works with new profiles app
  - Verify session authentication works for profile endpoints
  - Verify CSRF protection configured correctly for CORS
  - Verify unauthorized users cannot access protected endpoints (403/401)
  - _Requirements: Authentication and authorization_


- [x] 22.3 Performance and optimization check
  - Verify database queries optimized (use `select_related` and `prefetch_related` where appropriate)
  - Check N+1 query issues on profile list and follow lists
  - Verify pagination works correctly for large datasets
  - Test frontend performance with many projects and skill tags
  - _Requirements: Performance and scalability_

- [x] 22.4 Final integration checkpoint
  - Ensure all migrations applied cleanly on fresh database
  - Ensure all backend tests pass
  - Ensure all frontend tests pass
  - Ensure no console errors or warnings in browser
  - Ask the user if questions arise or if ready to deploy.

---

## Notes

- **Optional Task Marker (`*`)**: Tasks marked with `*` are optional test-related sub-tasks. They can be skipped for faster MVP delivery but are recommended for production quality.
- **Property-Based Tests**: Each property test validates a universal correctness property from the design document across 100+ randomized inputs using Hypothesis (Python).
- **Requirements Traceability**: Each task explicitly references the requirements it implements for full traceability.
- **Checkpoints**: Multiple checkpoints ensure incremental validation — ensure tests pass and ask user before proceeding to next phase.
- **Integration Focus**: Tasks are structured to build incrementally: models → services → serializers → views → routes → frontend API → frontend pages → tests.
- **Existing Patterns**: All implementations follow existing project patterns for Django views (DRF function-based views), authentication (CorsSessionAuthentication), and frontend (Next.js App Router, React Query hooks).

---

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1.1"]
    },
    {
      "id": 1,
      "tasks": ["1.2", "1.3", "1.4"]
    },
    {
      "id": 2,
      "tasks": ["1.5"]
    },
    {
      "id": 3,
      "tasks": ["2.1", "2.2", "2.3"]
    },
    {
      "id": 4,
      "tasks": ["3.1", "3.2", "3.3", "3.4"]
    },
    {
      "id": 5,
      "tasks": ["4.1", "4.2", "4.3", "5.1", "5.2"]
    },
    {
      "id": 6,
      "tasks": ["6.1", "6.2", "6.3", "7.1", "7.2", "7.3", "7.4", "8.1"]
    },
    {
      "id": 7,
      "tasks": ["9.1", "9.2", "9.3"]
    },
    {
      "id": 8,
      "tasks": ["10.1"]
    },
    {
      "id": 9,
      "tasks": ["10.2", "10.3", "10.4", "10.5", "10.6", "10.7", "10.8"]
    },
    {
      "id": 10,
      "tasks": ["11.1", "11.2", "11.3", "11.4", "11.5", "11.6", "11.7", "11.8"]
    },
    {
      "id": 11,
      "tasks": ["12.1", "12.2", "12.3", "12.4", "12.5", "12.6"]
    },
    {
      "id": 12,
      "tasks": ["13.1", "13.2", "13.3", "13.4"]
    },
    {
      "id": 13,
      "tasks": ["13.5"]
    },
    {
      "id": 14,
      "tasks": ["14.1", "14.2"]
    },
    {
      "id": 15,
      "tasks": ["14.3", "14.4"]
    },
    {
      "id": 16,
      "tasks": ["15.1"]
    },
    {
      "id": 17,
      "tasks": ["15.2"]
    },
    {
      "id": 18,
      "tasks": ["16.1"]
    },
    {
      "id": 19,
      "tasks": ["16.2", "16.3"]
    },
    {
      "id": 20,
      "tasks": ["17.1"]
    },
    {
      "id": 21,
      "tasks": ["17.2", "17.3"]
    },
    {
      "id": 22,
      "tasks": ["18.1"]
    },
    {
      "id": 23,
      "tasks": ["18.2"]
    },
    {
      "id": 24,
      "tasks": ["19.1", "19.2"]
    },
    {
      "id": 25,
      "tasks": ["19.3"]
    },
    {
      "id": 26,
      "tasks": ["20.1"]
    },
    {
      "id": 27,
      "tasks": ["20.2"]
    },
    {
      "id": 28,
      "tasks": ["21.1", "21.2"]
    },
    {
      "id": 29,
      "tasks": ["21.3", "21.4"]
    },
    {
      "id": 30,
      "tasks": ["22.1", "22.2", "22.3"]
    },
    {
      "id": 31,
      "tasks": ["22.4"]
    }
  ]
}
```
