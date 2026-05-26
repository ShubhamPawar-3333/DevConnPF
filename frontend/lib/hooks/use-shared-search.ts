"use client";

import { useQuery } from "@tanstack/react-query";
import { useDebounce } from "@/lib/hooks/use-debounce";
import { validateSearchQuery } from "@/lib/utils/validation";
import type { SearchResult } from "@/lib/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Debounced search hook for shared repositories (public, no auth).
 *
 * Debounces the query by 300ms, validates it (3-300 chars),
 * and only executes the API call when the query is valid.
 * Results are cached for 30 seconds per (token, query) pair.
 *
 * @param token - The share token for the public repository
 * @param query - The raw search query string
 * @returns UseQueryResult containing search results
 */
export function useSharedSearch(token: string, query: string) {
  const debouncedQuery = useDebounce(query, 300);
  const validation = validateSearchQuery(debouncedQuery);
  const isValidQuery = validation.valid;

  return useQuery<SearchResult[]>({
    queryKey: ["shared-search", token, debouncedQuery],
    queryFn: async () => {
      const url = new URL(`${API_BASE_URL}/api/shared/${token}/search/`);
      url.searchParams.set("q", debouncedQuery);

      const response = await fetch(url.toString(), {
        method: "GET",
        headers: { "Accept": "application/json" },
      });

      if (!response.ok) {
        const error = { status: response.status, message: response.statusText };
        throw error;
      }

      const data = await response.json();
      return data.results ?? data;
    },
    enabled: isValidQuery && !!token,
    staleTime: 30_000, // Cache results for 30 seconds
  });
}
