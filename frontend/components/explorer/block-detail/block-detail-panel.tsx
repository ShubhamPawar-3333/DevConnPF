"use client";

import { useBlockDetail } from "@/lib/hooks/use-block-detail";
import { useLanguage } from "@/lib/hooks/use-language";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { CodeViewer } from "./code-viewer";
import { SummaryDisplay } from "@/components/explorer/summary-display";
import { AlertCircle, Link as LinkIcon } from "lucide-react";

interface BlockDetailPanelProps {
  repoId: number;
  blockId: number;
  onParentBlockClick?: (parentBlockName: string) => void;
}

/**
 * Displays block detail with a side-by-side layout:
 * source code on the left, AI summary on the right.
 * Shows block metadata (name, kind, line range) and handles summary states.
 * Requests summaries in the user's preferred language and shows a notice
 * if the preferred language is unavailable.
 */
export function BlockDetailPanel({
  repoId,
  blockId,
  onParentBlockClick,
}: BlockDetailPanelProps) {
  const preferredLanguage = useLanguage();
  const { data: block, isLoading, isError } = useBlockDetail(repoId, blockId, preferredLanguage);

  if (isLoading) {
    return <BlockDetailSkeleton />;
  }

  if (isError || !block) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-destructive">
          <AlertCircle className="h-4 w-4" />
          <span>Failed to load block details.</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Block metadata header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <CardTitle className="text-lg">{block.name}</CardTitle>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Badge variant="secondary">{block.kind}</Badge>
                <span>
                  Lines {block.startLine}–{block.endLine}
                </span>
              </div>
            </div>
          </div>
          {block.parentBlockName && (
            <div className="mt-2 flex items-center gap-1 text-sm">
              <LinkIcon className="h-3 w-3 text-muted-foreground" />
              <span className="text-muted-foreground">Parent:</span>
              <button
                onClick={() => onParentBlockClick?.(block.parentBlockName!)}
                className="text-primary underline-offset-4 hover:underline"
              >
                {block.parentBlockName}
              </button>
            </div>
          )}
        </CardHeader>
      </Card>

      {/* Side-by-side layout: code left, summary right */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Source code (left) */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Source Code</CardTitle>
          </CardHeader>
          <CardContent>
            <CodeViewer code={block.sourceCode} language={block.kind} />
          </CardContent>
        </Card>

        {/* Summary (right) */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">AI Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <SummaryDisplay
              status={block.summary?.status ?? "not_applicable"}
              text={block.summary?.text ?? null}
              summaryLanguage={block.summary?.language}
              preferredLanguage={preferredLanguage}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

/**
 * Loading skeleton for the block detail panel.
 */
function BlockDetailSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading block details">
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <div className="flex items-center gap-2 mt-1">
            <Skeleton className="h-5 w-16" />
            <Skeleton className="h-4 w-24" />
          </div>
        </CardHeader>
      </Card>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-24" />
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-24" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
