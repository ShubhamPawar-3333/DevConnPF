"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { BlockDetail, LanguageCode } from "@/lib/types/api";

/**
 * Fetches block detail (source code + summary) for a specific code block.
 * Includes the user's language preference as a query parameter so the
 * backend can return the summary in the preferred language when available.
 *
 * @param repoId - The repository ID
 * @param blockId - The block ID
 * @param lang - Optional language preference to request summaries in
 * @returns UseQueryResult containing the block detail
 */
export function useBlockDetail(repoId: number, blockId: number, lang?: LanguageCode) {
  const params: Record<string, string> = {};
  if (lang) {
    params.lang = lang;
  }

  return useQuery<BlockDetail>({
    queryKey: ["block-detail", repoId, blockId, lang ?? "default"],
    queryFn: () =>
      apiClient.get<BlockDetail>(
        `/api/repositories/${repoId}/blocks/${blockId}/`,
        Object.keys(params).length > 0 ? params : undefined
      ),
    enabled: repoId > 0 && blockId > 0,
  });
}
