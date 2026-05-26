"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { validateSearchQuery } from "@/lib/utils/validation";
import { useDebounce } from "@/lib/hooks/use-debounce";
import type { SearchResult } from "@/lib/types/api";

/**
 * Debounced search hook with validation and 30s cache.
 *
 * Debounces the query by 300ms, validates it (3-300 chars),
 * and only executes the API call when the query is valid.
 * Results are cached for 30 seconds per (repoId, query) pair.
 *
 * @param repoId - The repository ID to search within
 * @param query - The raw search query string
 * @returns UseQueryResult containing search results
 */
export function useSearch(repoId: number, query: string) {
  const debouncedQuery = useDebounce(query, 300);
  const validation = validateSearchQuery(debouncedQuery);
  const isValidQuery = validation.valid;

  return useQuery<SearchResult[]>({
    queryKey: ["search", repoId, debouncedQuery],
    queryFn: () =>
      apiClient.get<SearchResult[]>(
        `/api/repositories/${repoId}/search/`,
        { q: debouncedQuery }
      ),
    enabled: isValidQuery && repoId > 0,
    staleTime: 30_000, // Cache results for 30 seconds
  });
}
