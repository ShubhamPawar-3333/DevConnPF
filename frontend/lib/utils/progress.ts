import { ProgressReport } from "@/lib/types/api";

/**
 * Calculates the progress percentage from a ProgressReport.
 *
 * - Returns 0 when totalJobs is 0
 * - Clamps result between 0 and 100 inclusive
 * - Rounds to nearest integer
 *
 * @param report - A ProgressReport or object with totalJobs and completed fields
 * @returns A number between 0 and 100 inclusive
 */
export function calculateProgress(
  report: Pick<ProgressReport, "totalJobs" | "completed">
): number {
  const { totalJobs, completed } = report;

  if (totalJobs === 0) {
    return 0;
  }

  const percentage = Math.round((completed / totalJobs) * 100);

  return Math.max(0, Math.min(100, percentage));
}
