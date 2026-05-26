"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import type { RepositoryStatus } from "@/lib/types/api";

interface StatusBadgeProps {
  status: RepositoryStatus;
}

const STATUS_CONFIG: Record<
  RepositoryStatus,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  cloning: { label: "Cloning repository...", variant: "secondary" },
  extracting: { label: "Extracting files...", variant: "secondary" },
  parsing: { label: "Parsing code...", variant: "secondary" },
  summarizing: { label: "Generating summaries...", variant: "default" },
  ready: { label: "Complete", variant: "outline" },
  partially_summarized: { label: "Partially complete", variant: "outline" },
  failed: { label: "Failed", variant: "destructive" },
};

/**
 * Displays a human-readable status badge for a repository's current processing status.
 * Maps each RepositoryStatus to a label and appropriate color variant.
 */
export function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status];

  return (
    <Badge variant={config.variant} aria-label={`Status: ${config.label}`}>
      {config.label}
    </Badge>
  );
}
