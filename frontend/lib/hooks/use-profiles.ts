"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { profilesApi } from "@/lib/api/profiles";
import type {
  Follow,
  GitHubImportPreview,
  PaginatedResponse,
  Profile,
  ProfileCreateData,
  ProfileOwner,
  ProfileUpdateData,
  ProjectAddData,
  ProjectEntry,
  ProjectReorderData,
  SearchResponse,
} from "@/lib/types/profiles";

// ---------------------------------------------------------------------------
// Query Keys
// ---------------------------------------------------------------------------

export const profileKeys = {
  all: ["profiles"] as const,
  profile: (slug: string) => ["profiles", slug] as const,
  myProfile: () => ["profiles", "me"] as const,
  followers: (slug: string, page: number) =>
    ["profiles", slug, "followers", page] as const,
  following: (slug: string, page: number) =>
    ["profiles", slug, "following", page] as const,
  search: (query: string, skillTag?: string, page?: number) =>
    ["profiles", "search", query, skillTag, page] as const,
  githubPreview: () => ["profiles", "github-preview"] as const,
};

// ---------------------------------------------------------------------------
// Task 14.3 — Profile hooks
// ---------------------------------------------------------------------------

/**
 * Fetch a public profile by slug.
 */
export function useProfile(
  slug: string,
  options?: Partial<UseQueryOptions<Profile>>
) {
  return useQuery<Profile>({
    queryKey: profileKeys.profile(slug),
    queryFn: () => profilesApi.getProfile(slug),
    enabled: Boolean(slug),
    ...options,
  });
}

/**
 * Fetch the authenticated user's own profile (owner view).
 */
export function useMyProfile(
  options?: Partial<UseQueryOptions<ProfileOwner>>
) {
  return useQuery<ProfileOwner>({
    queryKey: profileKeys.myProfile(),
    queryFn: () => profilesApi.getMyProfile(),
    retry: false, // Don't retry on 404 (user has no profile yet)
    ...options,
  });
}

/**
 * Create a new profile (onboarding).
 */
export function useCreateProfile() {
  const queryClient = useQueryClient();

  return useMutation<ProfileOwner, Error, ProfileCreateData>({
    mutationFn: (data) => profilesApi.createProfile(data),
    onSuccess: (profile) => {
      queryClient.setQueryData(profileKeys.myProfile(), profile);
      queryClient.setQueryData(profileKeys.profile(profile.slug), profile);
    },
  });
}

/**
 * Update an existing profile.
 */
export function useUpdateProfile(slug: string) {
  const queryClient = useQueryClient();

  return useMutation<ProfileOwner, Error, ProfileUpdateData>({
    mutationFn: (data) => profilesApi.updateProfile(slug, data),
    onSuccess: (profile) => {
      queryClient.setQueryData(profileKeys.myProfile(), profile);
      // Invalidate the old slug in case slug changed
      queryClient.invalidateQueries({ queryKey: ["profiles"] });
    },
  });
}

/**
 * Fetch GitHub profile data for import preview.
 */
export function useGitHubImportPreview(
  options?: Partial<UseQueryOptions<GitHubImportPreview>>
) {
  return useQuery<GitHubImportPreview>({
    queryKey: profileKeys.githubPreview(),
    queryFn: () => profilesApi.previewGitHubImport(),
    enabled: false, // Only fetch when explicitly triggered
    retry: false,
    ...options,
  });
}

/**
 * Apply selected GitHub data to the profile.
 */
export function useApplyGitHubImport() {
  const queryClient = useQueryClient();

  return useMutation<ProfileOwner, Error, string[]>({
    mutationFn: (fields) => profilesApi.applyGitHubImport(fields),
    onSuccess: (profile) => {
      queryClient.setQueryData(profileKeys.myProfile(), profile);
      queryClient.setQueryData(profileKeys.profile(profile.slug), profile);
    },
  });
}

// ---------------------------------------------------------------------------
// Task 14.4 — Project hooks
// ---------------------------------------------------------------------------

/**
 * Add a project entry to the authenticated user's profile.
 */
export function useAddProject() {
  const queryClient = useQueryClient();

  return useMutation<ProjectEntry, Error, ProjectAddData>({
    mutationFn: (data) => profilesApi.addProject(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: profileKeys.myProfile() });
    },
  });
}

/**
 * Remove a project entry from the authenticated user's profile.
 */
export function useRemoveProject() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, number>({
    mutationFn: (projectId) => profilesApi.removeProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: profileKeys.myProfile() });
    },
  });
}

/**
 * Reorder project entries on the authenticated user's profile.
 */
export function useReorderProjects() {
  const queryClient = useQueryClient();

  return useMutation<ProjectEntry[], Error, ProjectReorderData>({
    mutationFn: (data) => profilesApi.reorderProjects(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: profileKeys.myProfile() });
    },
  });
}

// ---------------------------------------------------------------------------
// Task 14.4 — Follow hooks
// ---------------------------------------------------------------------------

/**
 * Follow a user by slug.
 */
export function useFollow(slug: string) {
  const queryClient = useQueryClient();

  return useMutation<Follow, Error>({
    mutationFn: () => profilesApi.followUser(slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: profileKeys.profile(slug) });
      queryClient.invalidateQueries({ queryKey: profileKeys.myProfile() });
    },
  });
}

/**
 * Unfollow a user by slug.
 */
export function useUnfollow(slug: string) {
  const queryClient = useQueryClient();

  return useMutation<void, Error>({
    mutationFn: () => profilesApi.unfollowUser(slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: profileKeys.profile(slug) });
      queryClient.invalidateQueries({ queryKey: profileKeys.myProfile() });
    },
  });
}

/**
 * Fetch a paginated list of followers for a profile.
 */
export function useFollowers(slug: string, page = 1) {
  return useQuery<PaginatedResponse<Follow>>({
    queryKey: profileKeys.followers(slug, page),
    queryFn: () => profilesApi.getFollowers(slug, page),
    enabled: Boolean(slug),
  });
}

/**
 * Fetch a paginated list of profiles a user is following.
 */
export function useFollowing(slug: string, page = 1) {
  return useQuery<PaginatedResponse<Follow>>({
    queryKey: profileKeys.following(slug, page),
    queryFn: () => profilesApi.getFollowing(slug, page),
    enabled: Boolean(slug),
  });
}

/**
 * Search profiles by query string with optional skill tag filter.
 */
export function useSearchProfiles(
  query: string,
  skillTag?: string,
  page = 1
) {
  return useQuery<SearchResponse>({
    queryKey: profileKeys.search(query, skillTag, page),
    queryFn: () => profilesApi.searchProfiles(query, skillTag, page),
    enabled: query.length >= 1 && query.length <= 200,
  });
}
