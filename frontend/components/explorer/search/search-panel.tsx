"use client";

import * as React from "react";
import { useState } from "react";
import { Search, AlertCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useSearch } from "@/lib/hooks/use-search";
import { validateSearchQuery } from "@/lib/utils/validation";
import { SearchResultItem } from "./search-result-item";
import type { SearchResult } from "@/lib/types/api";

export interface SearchPanelProps {
  repoId: number;
  onResultSelect: (result: SearchResult) => void;
}

const MAX_RESULTS = 50;

/**
 * Search panel with debounced input, validation feedback, and results list.
 *
 * Uses the useSearch hook which internally handles debouncing (300ms)
 * and validation. This component manages the query state and renders
 * appropriate UI states: validation messages, loading, results, empty state,
 * and error state.
 */
export function SearchPanel({ repoId, onResultSelect }: SearchPanelProps) {
  const [query, setQuery] = useState("");
  const { data: results, isLoading, isError } = useSearch(repoId, query);
  const validation = validateSearchQuery(query);

  // Determine if we should show validation messages
  const showTooShort = !validation.valid && validation.reason === "too_short" && query.length > 0;
  const showTooLong = !validation.valid && validation.reason === "too_long";

  // Determine if we have a valid query that has been searched
  const hasValidQuery = validation.valid;
  const hasResults = results && results.length > 0;
  const hasNoResults = results && results.length === 0 && hasValidQuery;

  // Limit displayed results to 50
  const displayedResults = results?.slice(0, MAX_RESULTS);

  return (
    <div className="space-y-4">
      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search summaries... (e.g., 'where is auth handled')"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-10"
          aria-label="Search summaries"
          aria-describedby={
            showTooShort ? "search-validation-short" :
            showTooLong ? "search-validation-long" :
            undefined
          }
        />
      </div>

      {/* Validation Messages */}
      {showTooShort && (
        <p
          id="search-validation-short"
          className="text-sm text-muted-foreground"
          role="status"
        >
          Type at least 3 characters to search
        </p>
      )}
      {showTooLong && (
        <p
          id="search-validation-long"
          className="text-sm text-destructive"
          role="alert"
        >
          Query must be 300 characters or less
        </p>
      )}

      {/* Loading State */}
      {isLoading && hasValidQuery && (
        <div className="space-y-3" aria-label="Loading search results">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="p-3 rounded-md border border-border">
              <Skeleton className="h-4 w-3/4 mb-2" />
              <Skeleton className="h-3 w-1/2 mb-2" />
              <Skeleton className="h-3 w-full" />
            </div>
          ))}
        </div>
      )}

      {/* Error State */}
      {isError && (
        <div className="flex items-center gap-2 p-4 rounded-md border border-destructive/50 bg-destructive/10">
          <AlertCircle className="h-4 w-4 text-destructive shrink-0" />
          <p className="text-sm text-destructive">
            Search could not be completed
          </p>
        </div>
      )}

      {/* Empty State */}
      {hasNoResults && !isLoading && !isError && (
        <div className="text-center py-8">
          <Search className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground">
            No matches found. Try different keywords.
          </p>
        </div>
      )}

      {/* Results List */}
      {hasResults && !isLoading && !isError && (
        <div className="space-y-2" role="list" aria-label="Search results">
          {displayedResults!.map((result) => (
            <div key={`${result.fileId}-${result.blockId ?? "file"}`} role="listitem">
              <SearchResultItem
                result={result}
                onSelect={() => onResultSelect(result)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
