"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { ProgressReport, RepositoryStatus } from "@/lib/types/api";

const POLL_INTERVAL = 5000; // 5 seconds

const TERMINAL_STATUSES: RepositoryStatus[] = [
  "ready",
  "partially_summarized",
  "failed",
];

/**
 * Polls repository progress every 5 seconds.
 * Automatically stops polling when a terminal status is reached
 * ("ready", "partially_summarized", or "failed").
 *
 * @param repoId - The repository ID
 * @param options - Optional configuration (enabled flag)
 * @returns UseQueryResult containing the progress report
 */
export function useRepositoryProgress(
  repoId: number,
  options?: { enabled?: boolean }
) {
  return useQuery<ProgressReport>({
    queryKey: ["repository-progress", repoId],
    queryFn: () =>
      apiClient.get<ProgressReport>(
        `/api/repositories/${repoId}/progress/`
      ),
    enabled: (options?.enabled ?? true) && repoId > 0,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && TERMINAL_STATUSES.includes(status)) {
        return false; // Stop polling on terminal status
      }
      return POLL_INTERVAL;
    },
  });
}
