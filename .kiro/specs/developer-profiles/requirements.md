# Requirements Document

## Introduction

Developer Profiles with Project Pages is the identity layer of the Developer Super-App. It provides developers with a standalone professional profile — similar to LinkedIn for developers — where they curate their own identity, skills, professional history, and projects. Profiles are created and managed entirely by the user; GitHub OAuth is used only for authentication. An optional "Import from GitHub" feature allows users to pull their avatar and bio as a convenience, but the profile remains user-owned and user-controlled. Each profile includes a projects section that links directly to the AI Codebase Explorer, creating a seamless flow from identity to work. The feature also introduces networking capabilities (follow/unfollow) and is designed to support a future social activity feed.

## Glossary

- **Profile_Service**: The backend service responsible for creating, reading, updating, and managing developer profile data.
- **Profile_Page**: The frontend page that renders a developer's public-facing profile information.
- **Project_Page**: A section within a developer's profile that displays their projects and links to the AI Codebase Explorer.
- **Follow_Service**: The service responsible for managing follow/unfollow relationships between developers.
- **GitHub_Import_Service**: The optional service that fetches avatar and bio from GitHub when explicitly triggered by the user.
- **Slug**: A URL-friendly unique identifier chosen by the developer, used in profile URLs.
- **Skill_Tag**: A keyword representing a technology or competency associated with a developer's profile.
- **Project_Entry**: A record linking a developer's profile to a repository in the AI Codebase Explorer.
- **Visitor**: Any user (authenticated or unauthenticated) viewing a developer's public profile.
- **Onboarding_Flow**: The guided process a new user goes through to create their profile after first authentication.

## Requirements

### Requirement 1: Profile Creation and Onboarding

**User Story:** As a new developer, I want to create my own profile after signing up, so that I have a unique professional identity on the platform.

#### Acceptance Criteria

1. WHEN an authenticated User does not yet have a profile, THE Profile_Service SHALL present the Onboarding_Flow prompting the User to enter a display name (required, 2–100 characters), Slug (required), bio (optional, maximum 500 characters), and Skill_Tags (optional, maximum 20 tags, each up to 50 characters).
2. WHEN a User submits the Onboarding_Flow with all required fields valid, THE Profile_Service SHALL create a profile with the provided information and a status of "active".
3. THE Profile_Service SHALL require a unique Slug during onboarding that conforms to the pattern: lowercase letters, numbers, and hyphens only, starting with a letter, between 3 and 40 characters.
4. IF the chosen Slug is already taken, THEN THE Profile_Service SHALL return a validation error indicating the Slug is unavailable.
5. WHILE a User has not completed the Onboarding_Flow, THE Profile_Service SHALL redirect the User to the onboarding page when accessing profile-dependent features.
6. IF the Onboarding_Flow submission contains invalid or missing required fields, THEN THE Profile_Service SHALL return a validation error response with field-level error descriptions and SHALL NOT create the profile.

### Requirement 2: Profile Viewing

**User Story:** As a visitor, I want to view a developer's public profile, so that I can learn about their skills and projects.

#### Acceptance Criteria

1. WHEN a Visitor navigates to a profile URL using a Slug, THE Profile_Page SHALL display the developer's display name, avatar, bio, location, website URL, Skill_Tags, and Project_Entries, omitting any optional field (avatar, location, website URL) that has not been set by the profile owner.
2. THE Profile_Page SHALL be accessible without authentication.
3. WHEN a Visitor views a profile, THE Profile_Page SHALL display the developer's Skill_Tags as a list of labeled badges, showing all Skill_Tags (up to the maximum of 20) without truncation.
4. WHEN a Visitor views a profile, THE Profile_Page SHALL display the total count of followers and the total count of developers the profile owner follows, each as a numeric value starting from 0.
5. IF the requested Slug does not correspond to an existing profile with a status of "active", THEN THE Profile_Service SHALL return a 404 response.
6. WHEN a Visitor views a profile that has zero Skill_Tags or zero Project_Entries, THE Profile_Page SHALL display the corresponding section as empty with no error state.
7. WHEN a Visitor views a profile with Project_Entries, THE Profile_Page SHALL display the Project_Entries in the custom display order set by the profile owner.

### Requirement 3: Profile Editing

**User Story:** As a developer, I want to edit my profile information, so that I can keep my professional identity accurate and up to date.

#### Acceptance Criteria

1. WHEN an authenticated User submits profile updates, THE Profile_Service SHALL update the display name (maximum 100 characters), bio (maximum 500 characters), location (maximum 100 characters), website URL (maximum 200 characters, must be a valid HTTP or HTTPS URL), avatar URL, and Skill_Tags for that User's profile.
2. IF a User who is not the profile owner attempts to edit a profile, THEN THE Profile_Service SHALL reject the request with a 403 response and leave the profile data unchanged.
3. WHEN an authenticated User updates their Skill_Tags, THE Profile_Service SHALL accept a list of up to 20 Skill_Tags, each with a maximum length of 50 characters.
4. IF a profile update request contains invalid data, THEN THE Profile_Service SHALL return a 400 response with field-level error descriptions and leave the existing profile data unchanged.
5. WHEN an authenticated User updates their Slug, THE Profile_Service SHALL validate that the new Slug is unique and conforms to the pattern: lowercase letters, numbers, and hyphens only, starting with a letter, between 3 and 40 characters.
6. WHEN an authenticated User uploads an avatar, THE Profile_Service SHALL accept image files up to 2 MB in size and in PNG, JPEG, or WebP format.
7. IF an authenticated User uploads an avatar that exceeds 2 MB or is not in PNG, JPEG, or WebP format, THEN THE Profile_Service SHALL reject the upload with a 400 response indicating the validation failure reason and leave the existing avatar unchanged.
8. IF an authenticated User submits a Slug that is already taken or does not conform to the required pattern, THEN THE Profile_Service SHALL return a 400 response indicating the Slug validation failure reason and leave the existing Slug unchanged.

### Requirement 4: Optional GitHub Import

**User Story:** As a developer, I want to optionally import my avatar and bio from GitHub, so that I can quickly populate my profile without typing everything manually.

#### Acceptance Criteria

1. WHEN an authenticated User triggers a GitHub import, THE GitHub_Import_Service SHALL fetch the User's current avatar URL, name, and bio from the GitHub API using the stored encrypted token within a timeout of 10 seconds.
2. WHEN the GitHub API returns data, THE GitHub_Import_Service SHALL present the fetched avatar URL, display name, and bio fields to the User for review before applying them to the profile, displaying each field's current profile value alongside the fetched GitHub value.
3. WHEN the User confirms the imported data, THE GitHub_Import_Service SHALL update only the fields the User selects to overwrite, applying the same validation rules as profile editing (display name max length, bio max length, avatar URL format).
4. IF the GitHub API request fails or does not respond within 10 seconds, THEN THE GitHub_Import_Service SHALL return an error response indicating the failure reason and leave the existing profile data unchanged.
5. IF the User does not have a stored GitHub token, THEN THE GitHub_Import_Service SHALL inform the User that GitHub import is unavailable and prompt them to re-authenticate with GitHub.
6. IF the stored GitHub token is expired or revoked, THEN THE GitHub_Import_Service SHALL inform the User that their GitHub authorization is invalid and prompt them to re-authenticate with GitHub.
7. IF the GitHub API returns a null or empty value for any of the fetched fields, THEN THE GitHub_Import_Service SHALL omit that field from the review presentation and SHALL NOT overwrite the existing profile value for that field.

### Requirement 5: Project Pages

**User Story:** As a developer, I want to showcase my projects on my profile, so that visitors can see my work and explore the codebase directly.

#### Acceptance Criteria

1. WHEN an authenticated User adds a project to their profile, THE Profile_Service SHALL create a Project_Entry linking the profile to an existing Repository owned by that User in the AI Codebase Explorer.
2. WHEN a Visitor views a Project_Entry on a profile, THE Project_Page SHALL display the project name, custom description, primary language, and a link to the AI Codebase Explorer view.
3. WHEN a Visitor clicks the explorer link on a Project_Entry, THE Project_Page SHALL navigate to the AI Codebase Explorer for that repository.
4. THE Profile_Service SHALL allow a maximum of 50 Project_Entries per profile.
5. WHEN an authenticated User removes a Project_Entry, THE Profile_Service SHALL delete the link between the profile and the repository without affecting the underlying Repository data.
6. WHEN an authenticated User reorders their Project_Entries, THE Profile_Service SHALL persist the custom display order.
7. WHEN an authenticated User adds a Project_Entry, THE Profile_Service SHALL allow the User to provide a custom project description of up to 300 characters, independent of the repository name.
8. IF an authenticated User attempts to add a Project_Entry and the profile already contains 50 Project_Entries, THEN THE Profile_Service SHALL reject the request with an error indicating the maximum project limit has been reached.
9. IF an authenticated User attempts to add a Project_Entry for a Repository that is already linked to their profile, THEN THE Profile_Service SHALL reject the request with an error indicating the repository is already added.
10. IF an authenticated User attempts to add a Project_Entry for a Repository that does not exist or is not owned by that User, THEN THE Profile_Service SHALL reject the request with an error indicating the repository is unavailable.

### Requirement 6: Follow and Unfollow

**User Story:** As a developer, I want to follow other developers, so that I can build my professional network and stay updated on their activity.

#### Acceptance Criteria

1. WHEN an authenticated User follows another developer, THE Follow_Service SHALL create a follow relationship between the two Users and return the created relationship record.
2. WHEN an authenticated User unfollows a developer, THE Follow_Service SHALL remove the follow relationship between the two Users.
3. IF a User attempts to follow themselves, THEN THE Follow_Service SHALL reject the request with a validation error indicating that self-follow is not permitted.
4. IF a User attempts to follow a developer they already follow, THEN THE Follow_Service SHALL return the existing relationship without creating a duplicate.
5. IF a User attempts to follow a developer whose profile does not exist or is not active, THEN THE Follow_Service SHALL return a 404 error indicating the target profile was not found.
6. IF a User attempts to unfollow a developer they do not currently follow, THEN THE Follow_Service SHALL return a 404 error indicating no follow relationship exists.
7. WHEN a follow relationship is created or removed, THE Follow_Service SHALL update the follower and following counts on both affected profiles to remain consistent with the actual number of relationships.
8. WHEN an authenticated User requests their followers list, THE Follow_Service SHALL return a paginated list of profiles that follow the User, with a default page size of 20 and a maximum page size of 100, ordered by follow date descending.
9. WHEN an authenticated User requests their following list, THE Follow_Service SHALL return a paginated list of profiles the User follows, with a default page size of 20 and a maximum page size of 100, ordered by follow date descending.

### Requirement 7: Profile Discovery and Search

**User Story:** As a developer, I want to search for other developers by name or skill, so that I can find and connect with relevant people.

#### Acceptance Criteria

1. WHEN a User submits a search query of between 1 and 200 characters, THE Profile_Service SHALL return active profiles where the query matches as a case-insensitive substring against display name, username, bio, or Skill_Tags.
2. THE Profile_Service SHALL return search results as a paginated list of up to 20 profiles per page, ordered by relevance where profiles matching display name or username are ranked above matches in bio or Skill_Tags.
3. WHEN a User filters search results by Skill_Tag, THE Profile_Service SHALL return only profiles that contain the specified Skill_Tag.
4. THE Profile_Service SHALL limit search results to active profiles only.
5. IF a search query is empty or exceeds 200 characters, THEN THE Profile_Service SHALL return a validation error indicating the query length constraint.
6. IF no profiles match the search query, THEN THE Profile_Service SHALL return an empty paginated list with a total count of zero.

### Requirement 8: Profile API Serialization

**User Story:** As a frontend developer, I want consistent and well-structured API responses for profile data, so that the frontend can reliably render profile information.

#### Acceptance Criteria

1. THE Profile_Service SHALL serialize profile responses including: slug, display_name, avatar_url, bio, location, website_url, skill_tags (as an array of strings), follower_count (integer), following_count (integer), projects (as an array of Project_Entry objects each containing project name, description, primary language, and explorer link), joined_date (ISO 8601 format), and github_username.
2. WHEN serializing a profile for a Visitor, THE Profile_Service SHALL exclude private fields: email, github_sync_status, and owner-only editable flags (is_editable_bio, is_editable_avatar, is_editable_skills).
3. WHEN serializing a profile for the profile owner, THE Profile_Service SHALL include additional fields: email, github_sync_status, and editable flags indicating which profile sections the owner can modify (is_editable_bio, is_editable_avatar, is_editable_skills).
4. THE Profile_Service SHALL serialize optional fields (bio, location, website_url, avatar_url, github_username) as null when no value has been set, rather than omitting the field from the response.
5. THE Profile_Service SHALL produce responses where serializing a valid Profile object and then deserializing the result yields an object with identical field values to the original.
6. IF a profile serialization request references a profile that does not exist, THEN THE Profile_Service SHALL return a 404 response.

### Requirement 9: Profile URL Routing

**User Story:** As a developer, I want a clean, memorable URL for my profile, so that I can share it easily.

#### Acceptance Criteria

1. THE Profile_Page SHALL be accessible at the URL path `/{slug}` where slug is the developer's unique profile Slug.
2. WHEN a User changes their Slug, THE Profile_Service SHALL immediately release the old Slug so that it returns a 404 response when requested.
3. THE Profile_Service SHALL validate that Slugs conform to the pattern: lowercase letters, numbers, and hyphens only, starting with a letter, between 3 and 40 characters in length.
4. IF a User attempts to claim a Slug that matches a reserved system route, THEN THE Profile_Service SHALL reject the request with a validation error indicating the Slug is unavailable.
5. THE Profile_Service SHALL maintain a configurable list of reserved Slugs that includes at minimum: "admin", "api", "auth", "settings", "dashboard", "login", "explore", "shared", "repos", and "search".
6. IF a Slug validation fails due to invalid format or length, THEN THE Profile_Service SHALL return a 400 response indicating the specific validation rule that was violated.
