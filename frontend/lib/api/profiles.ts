import { apiClient } from "@/lib/api/client";
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

export const profilesApi = {
  // --- Profile CRUD ---

  getProfile: (slug: string): Promise<Profile> =>
    apiClient.get(`/api/profiles/${slug}/`),

  getMyProfile: (): Promise<ProfileOwner> =>
    apiClient.get("/api/profiles/me/"),

  createProfile: (data: ProfileCreateData): Promise<ProfileOwner> =>
    apiClient.post("/api/profiles/me/", data),

  updateProfile: (slug: string, data: ProfileUpdateData): Promise<ProfileOwner> =>
    apiClient.put(`/api/profiles/${slug}/update/`, data),

  // --- GitHub import ---

  previewGitHubImport: (): Promise<GitHubImportPreview> =>
    apiClient.get("/api/profiles/me/github/preview/"),

  applyGitHubImport: (fields: string[]): Promise<ProfileOwner> =>
    apiClient.post("/api/profiles/me/github/apply/", { fields }),

  // --- Project management ---

  addProject: (data: ProjectAddData): Promise<ProjectEntry> =>
    apiClient.post("/api/profiles/me/projects/", data),

  removeProject: (projectId: number): Promise<void> =>
    apiClient.delete(`/api/profiles/me/projects/${projectId}/`),

  reorderProjects: (data: ProjectReorderData): Promise<ProjectEntry[]> =>
    apiClient.put("/api/profiles/me/projects/reorder/", data),

  // --- Follow management ---

  followUser: (slug: string): Promise<Follow> =>
    apiClient.post(`/api/profiles/${slug}/follow/`),

  unfollowUser: (slug: string): Promise<void> =>
    apiClient.delete(`/api/profiles/${slug}/unfollow/`),

  getFollowers: (
    slug: string,
    page = 1,
    pageSize = 20
  ): Promise<PaginatedResponse<Follow>> =>
    apiClient.get(`/api/profiles/${slug}/followers/`, {
      page: String(page),
      page_size: String(pageSize),
    }),

  getFollowing: (
    slug: string,
    page = 1,
    pageSize = 20
  ): Promise<PaginatedResponse<Follow>> =>
    apiClient.get(`/api/profiles/${slug}/following/`, {
      page: String(page),
      page_size: String(pageSize),
    }),

  // --- Search and discovery ---

  searchProfiles: (
    query: string,
    skillTag?: string,
    page = 1
  ): Promise<SearchResponse> => {
    const params: Record<string, string> = { q: query, page: String(page) };
    if (skillTag) params.skill_tag = skillTag;
    return apiClient.get("/api/profiles/search/", params);
  },
};
