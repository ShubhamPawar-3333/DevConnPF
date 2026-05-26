import { FileTreeNode } from "@/lib/types/api";

/**
 * Extends FileTreeNode with expansion state for rendering.
 */
export interface RenderNode extends FileTreeNode {
  isExpanded: boolean;
  children: RenderNode[] | null;
}

/**
 * Transforms a file tree into a sorted, render-ready structure.
 *
 * Sort order:
 * - Directories appear before files
 * - Within each group, entries are sorted alphabetically (case-insensitive)
 * - Expanded directories have their children recursively sorted
 *
 * Pure function — does not mutate the input array or nodes.
 *
 * @param nodes - Array of FileTreeNode objects to sort
 * @param expandedPaths - Set of directory paths that are currently expanded
 * @returns Sorted array of RenderNode objects
 */
export function buildRenderTree(
  nodes: FileTreeNode[],
  expandedPaths: Set<string>
): RenderNode[] {
  const sorted = [...nodes].sort((a, b) => {
    if (a.type === "directory" && b.type === "file") return -1;
    if (a.type === "file" && b.type === "directory") return 1;
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
  });

  return sorted.map((node) => ({
    ...node,
    isExpanded: expandedPaths.has(node.path),
    children:
      node.type === "directory" && expandedPaths.has(node.path)
        ? buildRenderTree(node.children ?? [], expandedPaths)
        : null,
  }));
}
