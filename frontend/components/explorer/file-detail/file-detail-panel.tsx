"use client";

import { useFileDetail } from "@/lib/hooks/use-file-detail";
import { useLanguage } from "@/lib/hooks/use-language";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { BlockList } from "./block-list";
import { SummaryDisplay } from "@/components/explorer/summary-display";
import { FileText, AlertCircle } from "lucide-react";

interface FileDetailPanelProps {
  repoId: number;
  fileId: number;
  onBlockSelect?: (blockId: number) => void;
}

/**
 * Displays file detail information including path, language, AI summary,
 * and a list of code blocks. Handles loading and summary status states.
 * Requests summaries in the user's preferred language and shows a notice
 * if the preferred language is unavailable.
 */
export function FileDetailPanel({
  repoId,
  fileId,
  onBlockSelect,
}: FileDetailPanelProps) {
  const preferredLanguage = useLanguage();
  const { data: file, isLoading, isError } = useFileDetail(repoId, fileId, preferredLanguage);

  if (isLoading) {
    return <FileDetailSkeleton />;
  }

  if (isError || !file) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-destructive">
          <AlertCircle className="h-4 w-4" />
          <span>Failed to load file details.</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* File info header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-2 min-w-0">
              <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />
              <CardTitle className="truncate text-lg">{file.path}</CardTitle>
            </div>
            <Badge variant="outline" className="shrink-0">
              {file.language}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <SummaryDisplay
            status={file.summary?.status ?? "not_applicable"}
            text={file.summary?.text ?? null}
            summaryLanguage={file.summary?.language}
            preferredLanguage={preferredLanguage}
          />
        </CardContent>
      </Card>

      {/* Block list */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Code Blocks</CardTitle>
        </CardHeader>
        <CardContent>
          <BlockList
            blocks={file.blocks}
            onBlockSelect={onBlockSelect ?? (() => {})}
          />
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Loading skeleton for the file detail panel.
 */
function FileDetailSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading file details">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <Skeleton className="h-6 w-64" />
            <Skeleton className="h-5 w-16" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-28" />
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </CardContent>
      </Card>
    </div>
  );
}
