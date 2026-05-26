import { describe, it, expect } from "vitest";
import { buildRenderTree, RenderNode } from "./tree-sort";
import { FileTreeNode } from "@/lib/types/api";

function makeNode(
  overrides: Partial<FileTreeNode> & Pick<FileTreeNode, "name" | "type">
): FileTreeNode {
  return {
    id: 1,
    path: overrides.path ?? `/${overrides.name}`,
    language: null,
    summaryPreview: null,
    summaryStatus: "not_applicable",
    children: overrides.type === "directory" ? [] : null,
    ...overrides,
  };
}

describe("buildRenderTree", () => {
  it("returns an empty array for empty input", () => {
    const result = buildRenderTree([], new Set());
    expect(result).toEqual([]);
  });

  it("sorts directories before files", () => {
    const nodes: FileTreeNode[] = [
      makeNode({ name: "readme.md", type: "file" }),
      makeNode({ name: "src", type: "directory" }),
      makeNode({ name: "index.ts", type: "file" }),
      makeNode({ name: "lib", type: "directory" }),
    ];

    const result = buildRenderTree(nodes, new Set());
    const types = result.map((n) => n.type);

    expect(types).toEqual(["directory", "directory", "file", "file"]);
  });

  it("sorts alphabetically (case-insensitive) within each group", () => {
    const nodes: FileTreeNode[] = [
      makeNode({ name: "Zebra.ts", type: "file" }),
      makeNode({ name: "alpha.ts", type: "file" }),
      makeNode({ name: "Beta.ts", type: "file" }),
    ];

    const result = buildRenderTree(nodes, new Set());
    const names = result.map((n) => n.name);

    expect(names).toEqual(["alpha.ts", "Beta.ts", "Zebra.ts"]);
  });

  it("sorts directories alphabetically (case-insensitive)", () => {
    const nodes: FileTreeNode[] = [
      makeNode({ name: "utils", type: "directory" }),
      makeNode({ name: "Components", type: "directory" }),
      makeNode({ name: "api", type: "directory" }),
    ];

    const result = buildRenderTree(nodes, new Set());
    const names = result.map((n) => n.name);

    expect(names).toEqual(["api", "Components", "utils"]);
  });

  it("marks expanded directories with isExpanded: true", () => {
    const nodes: FileTreeNode[] = [
      makeNode({ name: "src", type: "directory", path: "/src" }),
      makeNode({ name: "lib", type: "directory", path: "/lib" }),
    ];

    const result = buildRenderTree(nodes, new Set(["/src"]));

    expect(result[0].name).toBe("lib");
    expect(result[0].isExpanded).toBe(false);
    expect(result[1].name).toBe("src");
    expect(result[1].isExpanded).toBe(true);
  });

  it("sets children to null for collapsed directories", () => {
    const nodes: FileTreeNode[] = [
      makeNode({
        name: "src",
        type: "directory",
        path: "/src",
        children: [makeNode({ name: "index.ts", type: "file", path: "/src/index.ts" })],
      }),
    ];

    const result = buildRenderTree(nodes, new Set());

    expect(result[0].isExpanded).toBe(false);
    expect(result[0].children).toBeNull();
  });

  it("recursively sorts children of expanded directories", () => {
    const nodes: FileTreeNode[] = [
      makeNode({
        name: "src",
        type: "directory",
        path: "/src",
        children: [
          makeNode({ name: "zebra.ts", type: "file", path: "/src/zebra.ts" }),
          makeNode({ name: "components", type: "directory", path: "/src/components", children: [] }),
          makeNode({ name: "alpha.ts", type: "file", path: "/src/alpha.ts" }),
        ],
      }),
    ];

    const result = buildRenderTree(nodes, new Set(["/src"]));
    const childNames = result[0].children!.map((n) => n.name);

    expect(childNames).toEqual(["components", "alpha.ts", "zebra.ts"]);
  });

  it("does not mutate the input array", () => {
    const nodes: FileTreeNode[] = [
      makeNode({ name: "b.ts", type: "file" }),
      makeNode({ name: "a.ts", type: "file" }),
    ];
    const originalOrder = nodes.map((n) => n.name);

    buildRenderTree(nodes, new Set());

    expect(nodes.map((n) => n.name)).toEqual(originalOrder);
  });

  it("preserves output length equal to input length", () => {
    const nodes: FileTreeNode[] = [
      makeNode({ name: "a", type: "file" }),
      makeNode({ name: "b", type: "directory" }),
      makeNode({ name: "c", type: "file" }),
    ];

    const result = buildRenderTree(nodes, new Set());

    expect(result.length).toBe(nodes.length);
  });

  it("handles deeply nested expanded directories", () => {
    const nodes: FileTreeNode[] = [
      makeNode({
        name: "root",
        type: "directory",
        path: "/root",
        children: [
          makeNode({
            name: "nested",
            type: "directory",
            path: "/root/nested",
            children: [
              makeNode({ name: "deep.ts", type: "file", path: "/root/nested/deep.ts" }),
            ],
          }),
        ],
      }),
    ];

    const result = buildRenderTree(nodes, new Set(["/root", "/root/nested"]));

    expect(result[0].isExpanded).toBe(true);
    expect(result[0].children![0].isExpanded).toBe(true);
    expect(result[0].children![0].children![0].name).toBe("deep.ts");
  });

  it("handles directories with null children when expanded", () => {
    const nodes: FileTreeNode[] = [
      makeNode({
        name: "empty",
        type: "directory",
        path: "/empty",
        children: null as unknown as FileTreeNode[],
      }),
    ];

    const result = buildRenderTree(nodes, new Set(["/empty"]));

    expect(result[0].isExpanded).toBe(true);
    expect(result[0].children).toEqual([]);
  });
});
