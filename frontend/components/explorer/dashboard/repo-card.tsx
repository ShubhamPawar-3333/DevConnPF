"use client";

import * as React from "react";
import { Github, Upload, Calendar, FileText } from "lucide-react";
import { format } from "date-fns";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Repository, RepositoryStatus } from "@/lib/types/api";

export interface RepoCardProps {
  repository: Repository;
  onClick: () => void;
}

const STATUS_BADGE_CONFIG: Record<
  RepositoryStatus,
  { label: string; className: string }
> = {
  ready: {
    label: "Ready",
    className: "bg-green-100 text-green-800 border-green-200",
  },
  summarizing: {
    label: "Summarizing",
    className: "bg-amber-100 text-amber-800 border-amber-200",
  },
  parsing: {
    label: "Parsing",
    className: "bg-amber-100 text-amber-800 border-amber-200",
  },
  cloning: {
    label: "Cloning",
    className: "bg-amber-100 text-amber-800 border-amber-200",
  },
  extracting: {
    label: "Extracting",
    className: "bg-amber-100 text-amber-800 border-amber-200",
  },
  partially_summarized: {
    label: "Partially Summarized",
    className: "bg-blue-100 text-blue-800 border-blue-200",
  },
  failed: {
    label: "Failed",
    className: "bg-red-100 text-red-800 border-red-200",
  },
};

/**
 * Repository card component for the dashboard.
 * Displays repository name, source type, status badge, file count, and ingestion date.
 * Clicking the card navigates to the repository tree view.
 */
export function RepoCard({ repository, onClick }: RepoCardProps) {
  const statusConfig = STATUS_BADGE_CONFIG[repository.status];
  const sourceLabel = repository.sourceType === "github" ? "GitHub" : "ZIP Upload";
  const SourceIcon = repository.sourceType === "github" ? Github : Upload;
  const formattedDate = format(new Date(repository.ingestedAt), "MMM d, yyyy");

  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-label={`Repository: ${repository.name}`}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h3 className="text-base font-semibold leading-tight">
              {repository.name}
            </h3>
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <SourceIcon className="h-3.5 w-3.5" />
              <span>{sourceLabel}</span>
            </div>
          </div>
          <Badge variant="outline" className={statusConfig.className}>
            {statusConfig.label}
          </Badge>
        </div>

        <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <FileText className="h-3.5 w-3.5" />
            <span>
              {repository.fileCount} {repository.fileCount === 1 ? "file" : "files"}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5" />
            <span>{formattedDate}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
