"use client";

import { useQuery } from "@tanstack/react-query";
import type { FileTreeNode } from "@/lib/types/api";

/**
 * Response shape from the public shared repository endpoint.
 */
export interface SharedRepositoryData {
  repository_id: number;
  repository_name: string;
  status: string;
  owner_username: string;
  attribution: string;
  search_enabled: boolean;
  read_only: boolean;
  tree: FileTreeNode[];
  branding: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Fetches a shared repository by its public token.
 * No authentication required.
 *
 * @param token - The share token from the URL
 * @returns UseQueryResult containing the shared repository data
 */
export function useSharedRepository(token: string) {
  return useQuery<SharedRepositoryData>({
    queryKey: ["shared-repository", token],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/shared/${token}/`, {
        method: "GET",
        headers: { "Accept": "application/json" },
      });

      if (!response.ok) {
        const error = { status: response.status, message: response.statusText };
        throw error;
      }

      return response.json();
    },
    enabled: !!token,
    retry: false, // Don't retry on 404
  });
}
