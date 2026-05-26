"use client";

import * as React from "react";
import { useEffect, useRef, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { useRepositoryProgress } from "@/lib/hooks/use-repository-progress";
import { calculateProgress } from "@/lib/utils/progress";
import { StatusBadge } from "./status-badge";
import type { RepositoryStatus } from "@/lib/types/api";

interface ProgressPanelProps {
  repoId: number;
  onComplete: () => void;
}

const TERMINAL_STATUSES: RepositoryStatus[] = [
  "ready",
  "partially_summarized",
  "failed",
];

const CONSECUTIVE_ERROR_THRESHOLD = 3;

/**
 * Displays real-time progress for repository ingestion and summarization.
 *
 * - Polls progress endpoint every 5 seconds via useRepositoryProgress hook
 * - Shows animated progress bar with percentage
 * - Displays completed/pending/failed job counts
 * - Tracks consecutive errors: shows warning banner after 3 failures
 * - Resets error counter on successful response
 * - Calls onComplete when a terminal status is reached
 * - Shows indeterminate state when totalJobs === 0
 */
export function ProgressPanel({ repoId, onComplete }: ProgressPanelProps) {
  const [consecutiveErrors, setConsecutiveErrors] = useState(0);
  const onCompleteRef = useRef(onComplete);
  const hasCalledComplete = useRef(false);

  // Keep onComplete ref up to date without triggering effects
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  const { data: progress, isError, isSuccess, dataUpdatedAt } = useRepositoryProgress(repoId);

  // Track consecutive errors
  useEffect(() => {
    if (isError) {
      setConsecutiveErrors((prev) => prev + 1);
    }
  }, [isError, dataUpdatedAt]);

  // Reset error counter on successful response
  useEffect(() => {
    if (isSuccess && progress) {
      setConsecutiveErrors(0);
    }
  }, [isSuccess, progress, dataUpdatedAt]);

  // Invoke onComplete when terminal status is reached
  useEffect(() => {
    if (
      progress?.status &&
      TERMINAL_STATUSES.includes(progress.status) &&
      !hasCalledComplete.current
    ) {
      hasCalledComplete.current = true;
      onCompleteRef.current();
    }
  }, [progress?.status]);

  const showWarningBanner = consecutiveErrors >= CONSECUTIVE_ERROR_THRESHOLD;
  const isIndeterminate = !progress || progress.totalJobs === 0;
  const percentage = progress ? calculateProgress(progress) : 0;

  return (
    <div className="space-y-4" role="region" aria-label="Ingestion progress">
      {/* Warning banner for consecutive errors */}
      {showWarningBanner && (
        <div
          className="flex items-center gap-2 rounded-md border border-yellow-300 bg-yellow-50 px-4 py-3 text-sm text-yellow-800 dark:border-yellow-700 dark:bg-yellow-950 dark:text-yellow-200"
          role="alert"
        >
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>
            Connectivity issue detected. Progress updates may be delayed.
          </span>
        </div>
      )}

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {isIndeterminate ? "Preparing..." : `${percentage}%`}
          </span>
          {progress && <StatusBadge status={progress.status} />}
        </div>
        <Progress
          value={isIndeterminate ? undefined : percentage}
          className={`h-3 ${isIndeterminate ? "animate-pulse" : ""}`}
          aria-label={
            isIndeterminate
              ? "Progress: indeterminate"
              : `Progress: ${percentage}%`
          }
        />
      </div>

      {/* Job counts */}
      {progress && progress.totalJobs > 0 && (
        <div className="flex justify-between text-sm text-muted-foreground">
          <span>{progress.completed} completed</span>
          <span>{progress.pending} pending</span>
          {progress.failed > 0 && (
            <span className="text-destructive">{progress.failed} failed</span>
          )}
        </div>
      )}
    </div>
  );
}
