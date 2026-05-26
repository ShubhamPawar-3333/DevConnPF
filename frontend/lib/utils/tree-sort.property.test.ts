import { describe, it, expect } from "vitest";
import fc from "fast-check";
import { buildRenderTree } from "./tree-sort";
import { FileTreeNode, SummaryStatus } from "@/lib/types/api";

/**
 * Property 1: File Tree Sort Order Consistency
 *
 * For any array of FileTreeNode objects, buildRenderTree() SHALL produce an output
 * where all directory entries appear before all file entries, directories are sorted
 * alphabetically (case-insensitive) among themselves, and files are sorted alphabetically
 * (case-insensitive) among themselves. This property holds recursively at every depth level.
 *
 * **Validates: Requirements 5.2, 5.7**
 */

const summaryStatusArb: fc.Arbitrary<SummaryStatus> = fc.constantFrom(
  "completed",
  "pending",
  "failed",
  "permanently_failed",
  "not_applicable"
);

/**
 * Generates a random FileTreeNode (file type).
 */
function fileNodeArb(pathPrefix: string): fc.Arbitrary<FileTreeNode> {
  return fc
    .record({
      id: fc.nat(),
      name: fc.stringMatching(/^[a-zA-Z][a-zA-Z0-9._-]{0,19}$/),
      language: fc.constantFrom("typescript", "python", "javascript", null),
      summaryPreview: fc.oneof(fc.constant(null), fc.string({ maxLength: 80 })),
      summaryStatus: summaryStatusArb,
    })
    .map((fields) => ({
      ...fields,
      path: `${pathPrefix}/${fields.name}`,
      type: "file" as const,
      children: null,
    }));
}

/**
 * Generates a random FileTreeNode (directory type) with optional children.
 */
function directoryNodeArb(
  pathPrefix: string,
  maxDepth: number
): fc.Arbitrary<FileTreeNode> {
  return fc
    .record({
      id: fc.nat(),
      name: fc.stringMatching(/^[a-zA-Z][a-zA-Z0-9._-]{0,19}$/),
      summaryStatus: summaryStatusArb,
    })
    .chain((fields) => {
      const dirPath = `${pathPrefix}/${fields.name}`;
      const childrenArb =
        maxDepth > 0
          ? fc.array(fileTreeNodeArb(dirPath, maxDepth - 1), { maxLength: 4 })
          : fc.constant([]);

      return childrenArb.map((children) => ({
        id: fields.id,
        name: fields.name,
        path: dirPath,
        type: "directory" as const,
        language: null,
        summaryPreview: null,
        summaryStatus: fields.summaryStatus,
        children,
      }));
    });
}

/**
 * Generates a random FileTreeNode (either file or directory).
 */
function fileTreeNodeArb(
  pathPrefix: string = "",
  maxDepth: number = 2
): fc.Arbitrary<FileTreeNode> {
  return fc.oneof(fileNodeArb(pathPrefix), directoryNodeArb(pathPrefix, maxDepth));
}

/**
 * Generates an array of random FileTreeNode objects.
 */
const fileTreeArrayArb = fc.array(fileTreeNodeArb("", 2), {
  minLength: 0,
  maxLength: 15,
});

/**
 * Helper: checks that all directories come before all files in a list.
 */
function directoriesPrecedeFiles(nodes: { type: string }[]): boolean {
  let seenFile = false;
  for (const node of nodes) {
    if (node.type === "file") {
      seenFile = true;
    } else if (node.type === "directory" && seenFile) {
      return false;
    }
  }
  return true;
}

/**
 * Helper: checks that names within a group are sorted alphabetically (case-insensitive).
 */
function isSortedCaseInsensitive(names: string[]): boolean {
  for (let i = 1; i < names.length; i++) {
    if (
      names[i - 1].localeCompare(names[i], undefined, { sensitivity: "base" }) > 0
    ) {
      return false;
    }
  }
  return true;
}

/**
 * Helper: recursively verifies sort order properties at every level.
 */
function verifySortOrderRecursive(
  nodes: ReturnType<typeof buildRenderTree>
): boolean {
  // 1. Directories precede files
  if (!directoriesPrecedeFiles(nodes)) return false;

  // 2. Directories sorted alphabetically among themselves
  const dirNames = nodes
    .filter((n) => n.type === "directory")
    .map((n) => n.name);
  if (!isSortedCaseInsensitive(dirNames)) return false;

  // 3. Files sorted alphabetically among themselves
  const fileNames = nodes
    .filter((n) => n.type === "file")
    .map((n) => n.name);
  if (!isSortedCaseInsensitive(fileNames)) return false;

  // 4. Recursively check children of expanded directories
  for (const node of nodes) {
    if (node.children !== null) {
      if (!verifySortOrderRecursive(node.children)) return false;
    }
  }

  return true;
}

describe("Property 1: File Tree Sort Order Consistency", () => {
  it("directories always precede files in the output", () => {
    fc.assert(
      fc.property(fileTreeArrayArb, (nodes) => {
        const result = buildRenderTree(nodes, new Set());
        expect(directoriesPrecedeFiles(result)).toBe(true);
      }),
      { numRuns: 200 }
    );
  });

  it("directories are sorted alphabetically (case-insensitive) among themselves", () => {
    fc.assert(
      fc.property(fileTreeArrayArb, (nodes) => {
        const result = buildRenderTree(nodes, new Set());
        const dirNames = result
          .filter((n) => n.type === "directory")
          .map((n) => n.name);
        expect(isSortedCaseInsensitive(dirNames)).toBe(true);
      }),
      { numRuns: 200 }
    );
  });

  it("files are sorted alphabetically (case-insensitive) among themselves", () => {
    fc.assert(
      fc.property(fileTreeArrayArb, (nodes) => {
        const result = buildRenderTree(nodes, new Set());
        const fileNames = result
          .filter((n) => n.type === "file")
          .map((n) => n.name);
        expect(isSortedCaseInsensitive(fileNames)).toBe(true);
      }),
      { numRuns: 200 }
    );
  });

  it("output length equals input length", () => {
    fc.assert(
      fc.property(fileTreeArrayArb, (nodes) => {
        const result = buildRenderTree(nodes, new Set());
        expect(result.length).toBe(nodes.length);
      }),
      { numRuns: 200 }
    );
  });

  it("does not mutate the input array", () => {
    fc.assert(
      fc.property(fileTreeArrayArb, (nodes) => {
        const originalNames = nodes.map((n) => n.name);
        buildRenderTree(nodes, new Set());
        expect(nodes.map((n) => n.name)).toEqual(originalNames);
      }),
      { numRuns: 200 }
    );
  });

  it("sort order holds recursively for expanded directories", () => {
    // Generate nodes and expand all directory paths
    fc.assert(
      fc.property(fileTreeArrayArb, (nodes) => {
        // Collect all directory paths to expand them all
        function collectDirPaths(
          items: FileTreeNode[],
          paths: Set<string>
        ): Set<string> {
          for (const item of items) {
            if (item.type === "directory") {
              paths.add(item.path);
              if (item.children) {
                collectDirPaths(item.children, paths);
              }
            }
          }
          return paths;
        }

        const expandedPaths = collectDirPaths(nodes, new Set());
        const result = buildRenderTree(nodes, expandedPaths);
        expect(verifySortOrderRecursive(result)).toBe(true);
      }),
      { numRuns: 200 }
    );
  });
});
