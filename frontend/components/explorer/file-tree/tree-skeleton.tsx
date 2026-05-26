"use client";

import { Skeleton } from "@/components/ui/skeleton";

/**
 * Loading placeholder for the file tree browser.
 * Renders skeleton rows matching the expected tree dimensions.
 */
export function TreeSkeleton() {
  return (
    <div className="space-y-2 p-4" role="status" aria-label="Loading file tree">
      {/* Simulate a directory with children */}
      <Skeleton className="h-6 w-48" />
      <Skeleton className="ml-4 h-6 w-40" />
      <Skeleton className="ml-4 h-6 w-56" />
      <Skeleton className="ml-4 h-6 w-36" />
      <Skeleton className="h-6 w-44" />
      <Skeleton className="ml-4 h-6 w-52" />
      <Skeleton className="ml-4 h-6 w-32" />
      <Skeleton className="h-6 w-40" />
      <Skeleton className="h-6 w-60" />
      <Skeleton className="h-6 w-48" />
    </div>
  );
}
