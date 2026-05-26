"use client";

import { useState, useCallback, useRef, useMemo } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useRepositoryTree } from "@/lib/hooks/use-repository-tree";
import { usePrefetchFileDetail } from "@/lib/hooks/use-file-detail";
import { useLanguage } from "@/lib/hooks/use-language";
import { buildRenderTree, type RenderNode } from "@/lib/utils/tree-sort";
import { TreeNode } from "./tree-node";
import { TreeSkeleton } from "./tree-skeleton";
import { AlertCircle, RefreshCw } from "lucide-react";

export interface FileTreeProps {
  repoId: number;
  onFileSelect: (fileId: number) => void;
  onBlockSelect: (blockId: number) => void;
  selectedFileId?: number;
}

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
 * Main File Tree Browser component.
 *
 * Fetches the repository tree, manages expand/collapse state,
 * renders nodes with virtual scrolling when 200+ visible nodes,
 * and supports hover prefetch for file details.
 */
export function FileTree({
  repoId,
  onFileSelect,
  onBlockSelect,
  selectedFileId,
}: FileTreeProps) {
  const { data: treeData, isLoading, isError, error, refetch } =
    useRepositoryTree(repoId);
  const preferredLanguage = useLanguage();
  const prefetchFileDetail = usePrefetchFileDetail(repoId, preferredLanguage);

  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const parentRef = useRef<HTMLDivElement>(null);

  // Build the sorted render tree
  const renderTree = useMemo(() => {
    if (!treeData) return [];
    return buildRenderTree(treeData, expandedPaths);
  }, [treeData, expandedPaths]);

  // Flatten for rendering (virtual or regular)
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

  const handleSelect = useCallback(
    (node: RenderNode) => {
      if (node.type === "file") {
        onFileSelect(node.id);
      }
    },
    [onFileSelect]
  );

  const handleHover = useCallback(
    (node: RenderNode) => {
      if (node.type !== "file") return;

      // Clear any existing timer
      if (hoverTimerRef.current) {
        clearTimeout(hoverTimerRef.current);
      }

      // Prefetch after 200ms delay
      hoverTimerRef.current = setTimeout(() => {
        prefetchFileDetail(node.id);
      }, 200);
    },
    [prefetchFileDetail]
  );

  // Loading state
  if (isLoading) {
    return <TreeSkeleton />;
  }

  // Error state
  if (isError) {
    const apiError = error as { status?: number; message?: string } | undefined;
    const is404 = apiError?.status === 404;

    return (
      <div className="flex flex-col items-center justify-center p-8 text-center gap-3">
        <AlertCircle className="w-8 h-8 text-destructive" />
        <p className="text-sm text-muted-foreground">
          {is404
            ? "Repository not found"
            : apiError?.message || "Failed to load file tree"}
        </p>
        {!is404 && (
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        )}
      </div>
    );
  }

  // Empty state
  if (!flatNodes.length) {
    return (
      <div className="flex items-center justify-center p-8">
        <p className="text-sm text-muted-foreground">No files in this repository</p>
      </div>
    );
  }

  // Virtual scrolling for large trees
  if (useVirtual) {
    return (
      <div
        ref={parentRef}
        className="h-full overflow-auto"
        role="tree"
        aria-label="File tree"
      >
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
                <TreeNode
                  node={node}
                  depth={depth}
                  onToggle={() => handleToggle(node.path)}
                  onSelect={() => handleSelect(node)}
                  onHover={() => handleHover(node)}
                  isSelected={node.type === "file" && node.id === selectedFileId}
                />
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Regular rendering for smaller trees
  return (
    <div className="overflow-auto h-full" role="tree" aria-label="File tree">
      {flatNodes.map(({ node, depth }) => (
        <TreeNode
          key={node.path}
          node={node}
          depth={depth}
          onToggle={() => handleToggle(node.path)}
          onSelect={() => handleSelect(node)}
          onHover={() => handleHover(node)}
          isSelected={node.type === "file" && node.id === selectedFileId}
        />
      ))}
    </div>
  );
}
