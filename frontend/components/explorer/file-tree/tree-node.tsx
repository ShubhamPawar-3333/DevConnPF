"use client";

import { ChevronRight, ChevronDown, Folder, File } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { truncateSummary } from "@/lib/utils/truncate";
import type { SummaryStatus } from "@/lib/types/api";
import type { RenderNode } from "@/lib/utils/tree-sort";

export interface TreeNodeProps {
  node: RenderNode;
  depth: number;
  onToggle: () => void;
  onSelect: () => void;
  onHover: () => void;
  isSelected?: boolean;
}

/**
 * Returns the status indicator character and color class for a given summary status.
 */
function getStatusIndicator(status: SummaryStatus): {
  symbol: string;
  className: string;
} {
  switch (status) {
    case "completed":
      return { symbol: "✓", className: "text-green-600" };
    case "pending":
      return { symbol: "⏳", className: "text-yellow-600" };
    case "failed":
    case "permanently_failed":
      return { symbol: "✗", className: "text-red-600" };
    case "not_applicable":
      return { symbol: "—", className: "text-gray-400" };
    default:
      return { symbol: "—", className: "text-gray-400" };
  }
}

/**
 * Renders a single node in the file tree.
 *
 * - Directories show a folder icon with expand/collapse chevron
 * - Files show a file icon with status indicator and optional summary preview
 * - Indentation is depth * 16px
 * - Hover triggers prefetch after parent manages the 200ms delay
 */
export function TreeNode({
  node,
  depth,
  onToggle,
  onSelect,
  onHover,
  isSelected = false,
}: TreeNodeProps) {
  const isDirectory = node.type === "directory";
  const statusIndicator = getStatusIndicator(node.summaryStatus);
  const summaryPreview =
    !isDirectory && node.summaryStatus === "completed"
      ? truncateSummary(node.summaryPreview)
      : "";

  const handleClick = () => {
    if (isDirectory) {
      onToggle();
    } else {
      onSelect();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <div
      className={cn(
        "flex items-center gap-1 px-2 py-1 cursor-pointer rounded-sm text-sm hover:bg-accent/50 transition-colors",
        isSelected && "bg-accent"
      )}
      style={{ paddingLeft: `${depth * 16 + 8}px` }}
      onClick={handleClick}
      onMouseEnter={onHover}
      onKeyDown={handleKeyDown}
      role="treeitem"
      aria-expanded={isDirectory ? node.isExpanded : undefined}
      aria-selected={isSelected}
      tabIndex={0}
    >
      {/* Chevron for directories */}
      {isDirectory ? (
        <span className="flex-shrink-0 w-4 h-4">
          {node.isExpanded ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )}
        </span>
      ) : (
        <span className="flex-shrink-0 w-4 h-4" />
      )}

      {/* Icon */}
      {isDirectory ? (
        <Folder className="flex-shrink-0 w-4 h-4 text-blue-500" />
      ) : (
        <File className="flex-shrink-0 w-4 h-4 text-muted-foreground" />
      )}

      {/* File/directory name */}
      <span className="truncate font-medium">{node.name}</span>

      {/* Status indicator for files */}
      {!isDirectory && (
        <span
          className={cn("flex-shrink-0 text-xs", statusIndicator.className)}
          aria-label={`Status: ${node.summaryStatus}`}
        >
          {statusIndicator.symbol}
        </span>
      )}

      {/* Summary preview for completed files */}
      {summaryPreview && (
        <span className="truncate text-xs text-muted-foreground ml-1">
          {summaryPreview}
        </span>
      )}
    </div>
  );
}
