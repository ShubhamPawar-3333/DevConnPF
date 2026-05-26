"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { FileDetail, LanguageCode } from "@/lib/types/api";

/**
 * Fetches file detail (summary + blocks) for a specific file.
 * Includes the user's language preference as a query parameter so the
 * backend can return the summary in the preferred language when available.
 *
 * @param repoId - The repository ID
 * @param fileId - The file ID
 * @param lang - Optional language preference to request summaries in
 * @returns UseQueryResult containing the file detail
 */
export function useFileDetail(repoId: number, fileId: number, lang?: LanguageCode) {
  const params: Record<string, string> = {};
  if (lang) {
    params.lang = lang;
  }

  return useQuery<FileDetail>({
    queryKey: ["file-detail", repoId, fileId, lang ?? "default"],
    queryFn: () =>
      apiClient.get<FileDetail>(
        `/api/repositories/${repoId}/files/${fileId}/`,
        Object.keys(params).length > 0 ? params : undefined
      ),
    enabled: repoId > 0 && fileId > 0,
  });
}

/**
 * Returns a function to prefetch file detail data.
 * Useful for hover-based prefetching to improve perceived performance.
 *
 * @param repoId - The repository ID
 * @param lang - Optional language preference to request summaries in
 * @returns A function that accepts a fileId and triggers prefetching
 */
export function usePrefetchFileDetail(repoId: number, lang?: LanguageCode) {
  const queryClient = useQueryClient();

  return (fileId: number) => {
    if (repoId > 0 && fileId > 0) {
      const params: Record<string, string> = {};
      if (lang) {
        params.lang = lang;
      }

      queryClient.prefetchQuery({
        queryKey: ["file-detail", repoId, fileId, lang ?? "default"],
        queryFn: () =>
          apiClient.get<FileDetail>(
            `/api/repositories/${repoId}/files/${fileId}/`,
            Object.keys(params).length > 0 ? params : undefined
          ),
      });
    }
  };
}
