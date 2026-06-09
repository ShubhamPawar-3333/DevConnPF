// Profile types matching backend serializers exactly

export interface ProjectEntry {
  id: number;
  repository_name: string;
  custom_description: string | null;
  primary_language: string | null;
  explorer_link: string;
  display_order: number;
  added_at: string; // ISO 8601
}

export interface Profile {
  slug: string;
  display_name: string;
  avatar_url: string | null;
  bio: string | null;
  location: string | null;
  website_url: string | null;
  skill_tags: string[];
  follower_count: number;
  following_count: number;
  projects: ProjectEntry[];
  joined_date: string; // ISO 8601
  github_username: string | null;
}

export interface ProfileOwner extends Profile {
  email: string;
  github_sync_status: string | null;
}

export interface ProfileMini {
  slug: string;
  display_name: string;
  avatar_url: string | null;
  bio: string | null;
}

export interface Follow {
  id: number;
  follower: ProfileMini;
  target: ProfileMini;
  created_at: string; // ISO 8601
}

export interface PaginatedResponse<T> {
  count: number;
  next: number | null;
  previous: number | null;
  results: T[];
}

export interface SearchResponse {
  count: number;
  results: Profile[];
}

// Request types
export interface ProfileCreateData {
  display_name: string;
  slug: string;
  bio?: string | null;
  location?: string | null;
  website_url?: string | null;
  skill_tags?: string[];
}

export interface ProfileUpdateData {
  display_name?: string;
  slug?: string;
  bio?: string | null;
  location?: string | null;
  website_url?: string | null;
  avatar_url?: string | null;
  skill_tags?: string[];
}

export interface ProjectAddData {
  repository_id: number;
  custom_description?: string | null;
}

export interface ProjectReorderItem {
  id: number;
  display_order: number;
}

export interface ProjectReorderData {
  projects: ProjectReorderItem[];
}

export interface GitHubImportPreview {
  github_data: {
    avatar_url?: string;
    display_name?: string;
    bio?: string;
  };
  current_profile: {
    avatar_url: string | null;
    display_name: string;
    bio: string | null;
  };
}
