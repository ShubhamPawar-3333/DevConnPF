"use client";

import { useState, useCallback, useMemo, useRef } from "react";
import { Search, AlertCircle, User as UserIcon } from "lucide-react";
import { useParams } from "next/navigation";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useSharedRepository } from "@/lib/hooks/use-shared-repository";
import { useSharedSearch } from "@/lib/hooks/use-shared-search";
import { validateSearchQuery } from "@/lib/utils/validation";
import { buildRenderTree, type RenderNode } from "@/lib/utils/tree-sort";
import type { SearchResult } from "@/lib/types/api";

/** Threshold for enabling virtual scrolling */
const VIRTUAL_SCROLL_THRESHOLD = 200;

/** Row height in pixels for virtual scrolling */
const ROW_HEIGHT = 32;

/**
 * Flattens a render tree into a list of nodes with their depth,
 * only including visible nodes (expanded directories show children).
 */
function flattenTree(
  nodes: RenderNode[],
  depth: number = 0
): Array<{ node: RenderNode; depth: number }> {
  const result: Array<{ node: RenderNode; depth: number }> = [];
  for (const node of nodes) {
    result.push({ node, depth });
    if (node.type === "directory" && node.isExpanded && node.children) {
      result.push(...flattenTree(node.children, depth + 1));
    }
  }
  return result;
}

/**
 * Public shared repository view page.
 *
 * Displays a read-only file tree with search, attribution banner,
 * and "Powered by DevConn" watermark. No authentication required.
 * No edit/delete/manage controls are visible.
 *
 * Handles 404 for invalid/expired tokens.
 */
export default function SharedViewPage() {
  const params = useParams<{ token: string }>();
  const token = params.token;

  const { data, isLoading, isError, error } = useSharedRepository(token);

  // File tree state
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const parentRef = useRef<HTMLDivElement>(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const { data: searchResults, isLoading: isSearching, isError: isSearchError } =
    useSharedSearch(token, searchQuery);
  const searchValidation = validateSearchQuery(searchQuery);

  // Build the sorted render tree
  const renderTree = useMemo(() => {
    if (!data?.tree) return [];
    return buildRenderTree(data.tree, expandedPaths);
  }, [data?.tree, expandedPaths]);

  // Flatten for rendering
  const flatNodes = useMemo(() => flattenTree(renderTree), [renderTree]);

  const useVirtual = flatNodes.length >= VIRTUAL_SCROLL_THRESHOLD;

  // Virtual scrolling setup
  const virtualizer = useVirtualizer({
    count: flatNodes.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 10,
    enabled: useVirtual,
  });

  const handleToggle = useCallback((path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  // 404 state for invalid/expired tokens
  if (isError) {
    const apiError = error as { status?: number } | undefined;
    if (apiError?.status === 404 || !apiError?.status) {
      return (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <AlertCircle className="w-12 h-12 text-muted-foreground mb-4" />
          <h1 className="text-xl font-semibold text-gray-900 mb-2">Not Available</h1>
          <p className="text-muted-foreground">
            This shared repository is no longer available.
          </p>
        </div>
      );
    }

    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <AlertCircle className="w-12 h-12 text-destructive mb-4" />
        <h1 className="text-xl font-semibold text-gray-900 mb-2">Error</h1>
        <p className="text-muted-foreground">
          Something went wrong loading this shared repository.
        </p>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-12 w-full" />
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (!data) return null;

  const showTooShort =
    !searchValidation.valid && searchValidation.reason === "too_short" && searchQuery.length > 0;
  const showTooLong = !searchValidation.valid && searchValidation.reason === "too_long";
  const hasValidQuery = searchValidation.valid;
  const hasResults = searchResults && searchResults.length > 0;
  const hasNoResults = searchResults && searchResults.length === 0 && hasValidQuery;

  return (
    <div className="space-y-6">
      {/* Attribution Banner */}
      <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
        <UserIcon className="h-5 w-5 text-blue-600 shrink-0" />
        <p className="text-sm text-blue-800">
          Shared by <span className="font-semibold">{data.owner_username}</span>
        </p>
      </div>

      {/* Repository Name */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{data.repository_name}</h1>
        <p className="text-sm text-muted-foreground mt-1">Read-only view</p>
      </div>

      {/* Search Panel */}
      <div className="space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search summaries... (e.g., 'where is auth handled')"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
            aria-label="Search summaries"
          />
        </div>

        {/* Validation Messages */}
        {showTooShort && (
          <p className="text-sm text-muted-foreground" role="status">
            Type at least 3 characters to search
          </p>
        )}
        {showTooLong && (
          <p className="text-sm text-destructive" role="alert">
            Query must be 300 characters or less
          </p>
        )}

        {/* Search Loading */}
        {isSearching && hasValidQuery && (
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

        {/* Search Error */}
        {isSearchError && (
          <div className="flex items-center gap-2 p-4 rounded-md border border-destructive/50 bg-destructive/10">
            <AlertCircle className="h-4 w-4 text-destructive shrink-0" />
            <p className="text-sm text-destructive">
              Search could not be completed
            </p>
          </div>
        )}

        {/* Search Empty State */}
        {hasNoResults && !isSearching && !isSearchError && (
          <div className="text-center py-6">
            <Search className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">
              No matches found. Try different keywords.
            </p>
          </div>
        )}

        {/* Search Results */}
        {hasResults && !isSearching && !isSearchError && (
          <div className="space-y-2" role="list" aria-label="Search results">
            {searchResults!.slice(0, 50).map((result: SearchResult) => (
              <SharedSearchResultItem
                key={`${result.fileId}-${result.blockId ?? "file"}`}
                result={result}
              />
            ))}
          </div>
        )}
      </div>

      {/* File Tree (read-only) */}
      {!hasResults && !isSearching && (
        <div className="border rounded-lg bg-white">
          <div className="px-4 py-3 border-b bg-gray-50">
            <h2 className="text-sm font-medium text-gray-700">Files</h2>
          </div>
          <div
            ref={parentRef}
            className="max-h-[600px] overflow-auto"
            role="tree"
            aria-label="File tree"
          >
            {useVirtual ? (
              <div
                style={{
                  height: `${virtualizer.getTotalSize()}px`,
                  width: "100%",
                  position: "relative",
                }}
              >
                {virtualizer.getVirtualItems().map((virtualItem) => {
                  const { node, depth } = flatNodes[virtualItem.index];
                  return (
                    <div
                      key={node.path}
                      style={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        width: "100%",
                        height: `${virtualItem.size}px`,
                        transform: `translateY(${virtualItem.start}px)`,
                      }}
                    >
                      <ReadOnlyTreeNode
                        node={node}
                        depth={depth}
                        onToggle={() => handleToggle(node.path)}
                      />
                    </div>
                  );
                })}
              </div>
            ) : (
              flatNodes.map(({ node, depth }) => (
                <ReadOnlyTreeNode
                  key={node.path}
                  node={node}
                  depth={depth}
                  onToggle={() => handleToggle(node.path)}
                />
              ))
            )}
            {flatNodes.length === 0 && (
              <div className="flex items-center justify-center p-8">
                <p className="text-sm text-muted-foreground">No files in this repository</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Powered by DevConn Watermark */}
      <div className="text-center pt-6 pb-2 border-t">
        <p className="text-xs text-muted-foreground">Powered by DevConn</p>
      </div>
    </div>
  );
}

// --- Read-Only Tree Node Component ---

interface ReadOnlyTreeNodeProps {
  node: RenderNode;
  depth: number;
  onToggle: () => void;
}

/**
 * Read-only tree node for the shared view.
 * No selection, no hover prefetch, no edit/delete controls.
 */
function ReadOnlyTreeNode({ node, depth, onToggle }: ReadOnlyTreeNodeProps) {
  const isDirectory = node.type === "directory";
  const paddingLeft = `${depth * 20 + 12}px`;

  return (
    <div
      className="flex items-center h-8 px-2 hover:bg-gray-50 cursor-default text-sm"
      style={{ paddingLeft }}
      role="treeitem"
      aria-expanded={isDirectory ? node.isExpanded : undefined}
    >
      {/* Expand/Collapse for directories */}
      {isDirectory ? (
        <button
          onClick={onToggle}
          className="mr-1 p-0.5 rounded hover:bg-gray-200 text-gray-500"
          aria-label={node.isExpanded ? "Collapse" : "Expand"}
        >
          <svg
            className={`w-3 h-3 transition-transform ${node.isExpanded ? "rotate-90" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      ) : (
        <span className="w-4 mr-1" />
      )}

      {/* Icon */}
      {isDirectory ? (
        <svg className="w-4 h-4 mr-2 text-blue-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
        </svg>
      ) : (
        <svg className="w-4 h-4 mr-2 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      )}

      {/* Name */}
      <span className="truncate text-gray-800">{node.name}</span>

      {/* Summary preview for files */}
      {!isDirectory && node.summaryPreview && (
        <span className="ml-3 text-xs text-muted-foreground truncate hidden sm:inline">
          {node.summaryPreview}
        </span>
      )}

      {/* Status indicator for files */}
      {!isDirectory && (
        <span className="ml-auto shrink-0">
          <StatusDot status={node.summaryStatus} />
        </span>
      )}
    </div>
  );
}

// --- Status Dot Component ---

function StatusDot({ status }: { status: string }) {
  switch (status) {
    case "completed":
      return <span className="w-2 h-2 rounded-full bg-green-500 inline-block" title="Summary available" />;
    case "pending":
      return <span className="w-2 h-2 rounded-full bg-yellow-400 inline-block" title="Summary pending" />;
    case "failed":
    case "permanently_failed":
      return <span className="w-2 h-2 rounded-full bg-red-500 inline-block" title="Summary failed" />;
    default:
      return <span className="w-2 h-2 rounded-full bg-gray-300 inline-block" title="Not applicable" />;
  }
}

// --- Shared Search Result Item ---

function SharedSearchResultItem({ result }: { result: SearchResult }) {
  return (
    <div
      className="p-3 rounded-md border border-border hover:bg-gray-50 transition-colors"
      role="listitem"
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs font-medium text-muted-foreground uppercase">
          {result.resultType}
        </span>
        <span className="text-sm font-medium text-gray-900 truncate">
          {result.filePath}
        </span>
      </div>
      {result.blockName && (
        <p className="text-xs text-muted-foreground mb-1">{result.blockName}</p>
      )}
      <p className="text-sm text-gray-600 line-clamp-2">{result.summaryExcerpt}</p>
    </div>
  );
}
