"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { FileTreeNode } from "@/lib/types/api";

/**
 * Fetches the file tree for a repository.
 *
 * @param repoId - The repository ID
 * @returns UseQueryResult containing the file tree nodes
 */
export function useRepositoryTree(repoId: number) {
  return useQuery<FileTreeNode[]>({
    queryKey: ["repository-tree", repoId],
    queryFn: () =>
      apiClient.get<FileTreeNode[]>(`/api/repositories/${repoId}/tree/`),
    enabled: repoId > 0,
  });
}
