"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { ShareInfo } from "@/lib/types/api";

/**
 * Mutation to enable sharing for a repository.
 * Invalidates the repository query cache on success.
 *
 * @param repoId - The repository ID
 * @returns UseMutationResult for enabling sharing
 */
export function useEnableSharing(repoId: number) {
  const queryClient = useQueryClient();

  return useMutation<ShareInfo, Error>({
    mutationFn: () =>
      apiClient.post<ShareInfo>(
        `/api/repositories/${repoId}/share/enable/`
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["repository", repoId],
      });
    },
  });
}

/**
 * Mutation to disable sharing for a repository.
 * Invalidates the repository query cache on success.
 *
 * @param repoId - The repository ID
 * @returns UseMutationResult for disabling sharing
 */
export function useDisableSharing(repoId: number) {
  const queryClient = useQueryClient();

  return useMutation<void, Error>({
    mutationFn: () =>
      apiClient.post<void>(
        `/api/repositories/${repoId}/share/disable/`
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["repository", repoId],
      });
    },
  });
}

/**
 * Mutation to regenerate the share URL for a repository.
 * Invalidates the repository query cache on success.
 *
 * @param repoId - The repository ID
 * @returns UseMutationResult for regenerating the share URL
 */
export function useRegenerateShareUrl(repoId: number) {
  const queryClient = useQueryClient();

  return useMutation<ShareInfo, Error>({
    mutationFn: () =>
      apiClient.post<ShareInfo>(
        `/api/repositories/${repoId}/share/regenerate/`
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["repository", repoId],
      });
    },
  });
}
