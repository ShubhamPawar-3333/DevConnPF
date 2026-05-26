"use client";

import * as React from "react";
import { FileText, Code } from "lucide-react";
import type { SearchResult } from "@/lib/types/api";
import { truncateSearchExcerpt } from "@/lib/utils/truncate";

export interface SearchResultItemProps {
  result: SearchResult;
  onSelect: () => void;
}

/**
 * Highlights matching terms in the excerpt by wrapping them in <mark> tags.
 * Splits the query into words and highlights each occurrence (case-insensitive).
 */
function highlightExcerpt(excerpt: string, query: string): React.ReactNode[] {
  if (!query || query.length < 3) {
    return [excerpt];
  }

  const terms = query
    .split(/\s+/)
    .filter((term) => term.length >= 2)
    .map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));

  if (terms.length === 0) {
    return [excerpt];
  }

  const pattern = new RegExp(`(${terms.join("|")})`, "gi");
  const parts = excerpt.split(pattern);

  return parts.map((part, index) => {
    if (pattern.test(part)) {
      // Reset lastIndex since we're reusing the regex
      pattern.lastIndex = 0;
      return (
        <mark
          key={index}
          className="bg-yellow-200 dark:bg-yellow-800 rounded-sm px-0.5"
        >
          {part}
        </mark>
      );
    }
    // Also reset for non-matching parts
    pattern.lastIndex = 0;
    return part;
  });
}

/**
 * Renders a single search result with file path, block name,
 * and highlighted summary excerpt.
 */
export function SearchResultItem({ result, onSelect }: SearchResultItemProps) {
  const Icon = result.resultType === "block" ? Code : FileText;
  const truncatedExcerpt = truncateSearchExcerpt(result.summaryExcerpt);

  return (
    <button
      type="button"
      onClick={onSelect}
      className="w-full text-left p-3 rounded-md border border-border hover:bg-accent hover:border-accent-foreground/20 transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      aria-label={`View ${result.resultType}: ${result.filePath}${result.blockName ? ` - ${result.blockName}` : ""}`}
    >
      <div className="flex items-start gap-2">
        <Icon className="h-4 w-4 mt-0.5 shrink-0 text-muted-foreground" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-foreground truncate">
            {result.filePath}
          </p>
          {result.blockName && (
            <p className="text-xs text-muted-foreground mt-0.5">
              {result.blockName}
            </p>
          )}
          <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
            {truncatedExcerpt}
          </p>
        </div>
      </div>
    </button>
  );
}

export { highlightExcerpt };
