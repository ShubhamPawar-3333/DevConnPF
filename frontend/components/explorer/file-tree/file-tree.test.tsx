import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FileTree } from "./file-tree";
import type { FileTreeNode } from "@/lib/types/api";

// Mock the hooks
const mockRefetch = vi.fn();
let mockTreeReturn: {
  data: FileTreeNode[] | undefined;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => void;
};

vi.mock("@/lib/hooks/use-repository-tree", () => ({
  useRepositoryTree: () => mockTreeReturn,
}));

vi.mock("@/lib/hooks/use-file-detail", () => ({
  usePrefetchFileDetail: () => vi.fn(),
}));

vi.mock("@/lib/hooks/use-language", () => ({
  useLanguage: () => "en",
}));

// Mock @tanstack/react-virtual to avoid jsdom measurement issues
vi.mock("@tanstack/react-virtual", () => ({
  useVirtualizer: () => ({
    getVirtualItems: () => [],
    getTotalSize: () => 0,
    measureElement: vi.fn(),
  }),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

const defaultProps = {
  repoId: 1,
  onFileSelect: vi.fn(),
  onBlockSelect: vi.fn(),
};

// Test data fixtures
const sampleTree: FileTreeNode[] = [
  {
    id: 3,
    name: "zebra.ts",
    path: "zebra.ts",
    type: "file",
    language: "typescript",
    summaryPreview: "A utility file for zebra operations",
    summaryStatus: "completed",
    children: null,
  },
  {
    id: 1,
    name: "src",
    path: "src",
    type: "directory",
    language: null,
    summaryPreview: null,
    summaryStatus: "not_applicable",
    children: [
      {
        id: 4,
        name: "index.ts",
        path: "src/index.ts",
        type: "file",
        language: "typescript",
        summaryPreview: "Main entry point",
        summaryStatus: "completed",
        children: null,
      },
      {
        id: 5,
        name: "utils",
        path: "src/utils",
        type: "directory",
        language: null,
        summaryPreview: null,
        summaryStatus: "not_applicable",
        children: [],
      },
    ],
  },
  {
    id: 2,
    name: "alpha.ts",
    path: "alpha.ts",
    type: "file",
    language: "typescript",
    summaryPreview: null,
    summaryStatus: "pending",
    children: null,
  },
  {
    id: 6,
    name: "docs",
    path: "docs",
    type: "directory",
    language: null,
    summaryPreview: null,
    summaryStatus: "not_applicable",
    children: [],
  },
];

describe("FileTree", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockTreeReturn = {
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      refetch: mockRefetch,
    };
  });

  describe("Loading state", () => {
    it("shows TreeSkeleton while loading", () => {
      mockTreeReturn = {
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
        refetch: mockRefetch,
      };

      render(<FileTree {...defaultProps} />, { wrapper: createWrapper() });

      expect(screen.getByRole("status", { name: "Loading file tree" })).toBeInTheDocument();
    });
  });

  describe("Error state", () => {
    it("shows error message with retry button on generic error", () => {
      mockTreeReturn = {
        data: undefined,
        isLoading: false,
        isError: true,
        error: { status: 500, message: "Internal server error" },
        refetch: mockRefetch,
      };

      render(<FileTree {...defaultProps} />, { wrapper: createWrapper() });

      expect(screen.getByText("Internal server error")).toBeInTheDocument();
      expect(screen.getByText("Retry")).toBeInTheDocument();
    });

    it("shows 'Repository not found' for 404 errors without retry button", () => {
      mockTreeReturn = {
        data: undefined,
        isLoading: false,
        isError: true,
        error: { status: 404, message: "Not found" },
        refetch: mockRefetch,
      };

      render(<FileTree {...defaultProps} />, { wrapper: createWrapper() });

      expect(screen.getByText("Repository not found")).toBeInTheDocument();
      expect(screen.queryByText("Retry")).not.toBeInTheDocument();
    });

    it("calls refetch when retry button is clicked", () => {
      mockTreeReturn = {
        data: undefined,
        isLoading: false,
        isError: true,
        error: { status: 500, message: "Server error" },
        refetch: mockRefetch,
      };

      render(<FileTree {...defaultProps} />, { wrapper: createWrapper() });

      fireEvent.click(screen.getByText("Retry"));
      expect(mockRefetch).toHaveBeenCalled();
    });
  });

  describe("Empty state", () => {
    it("shows empty state when tree has no nodes", () => {
      mockTreeReturn = {
        data: [],
        isLoading: false,
        isError: false,
        error: null,
        refetch: mockRefetch,
      };

      render(<FileTree {...defaultProps} />, { wrapper: createWrapper() });

      expect(screen.getByText("No files in this repository")).toBeInTheDocument();
    });
  });

  describe("Populated tree", () => {
    beforeEach(() => {
      mockTreeReturn = {
        data: sampleTree,
        isLoading: false,
        isError: false,
        error: null,
        refetch: mockRefetch,
      };
    });

    it("renders tree with correct sort order (directories before files)", () => {
      render(<FileTree {...defaultProps} />, { wrapper: createWrapper() });

      const treeItems = screen.getAllByRole("treeitem");

      // Directories first (alphabetical): docs, src
      // Then files (alphabetical): alpha.ts, zebra.ts
      expect(treeItems[0]).toHaveTextContent("docs");
      expect(treeItems[1]).toHaveTextContent("src");
      expect(treeItems[2]).toHaveTextContent("alpha.ts");
      expect(treeItems[3]).toHaveTextContent("zebra.ts");
    });

    it("renders the tree container with role='tree'", () => {
      render(<FileTree {...defaultProps} />, { wrapper: createWrapper() });

      expect(screen.getByRole("tree", { name: "File tree" })).toBeInTheDocument();
    });

    it("shows status indicators for files", () => {
      mockTreeReturn = {
        data: [
          {
            id: 1,
            name: "completed.ts",
            path: "completed.ts",
            type: "file",
            language: "typescript",
            summaryPreview: "A completed file",
            summaryStatus: "completed",
            children: null,
          },
          {
            id: 2,
            name: "pending.ts",
            path: "pending.ts",
            type: "file",
            language: "typescript",
            summaryPreview: null,
            summaryStatus: "pending",
            children: null,
          },
          {
            id: 3,
            name: "failed.ts",
            path: "failed.ts",
            type: "file",
            language: "typescript",
            summaryPreview: null,
            summaryStatus: "failed",
            children: null,
          },
        ],
        isLoading: false,
        isError: false,
        error: null,
        refetch: mockRefetch,
      };

      render(<FileTree {...defaultProps} />, { wrapper: createWrapper() });

      expect(screen.getByLabelText("Status: completed")).toHaveTextContent("✓");
      expect(screen.getByLabelText("Status: pending")).toHaveTextContent("⏳");
      expect(screen.getByLabelText("Status: failed")).toHaveTextContent("✗");
    });
  });

  describe("Expand/collapse interactions", () => {
    beforeEach(() => {
      mockTreeReturn = {
        data: sampleTree,
        isLoading: false,
        isError: false,
        error: null,
        refetch: mockRefetch,
      };
    });

    it("directories are collapsed by default (children not visible)", () => {
      render(<FileTree {...defaultProps} />, { wrapper: createWrapper() });

      // Children of "src" directory should not be visible initially
      expect(screen.queryByText("index.ts")).not.toBeInTheDocument();
      expect(screen.queryByText("utils")).not.toBeInTheDocument();
    });

    it("clicking a directory expands it to show children", () => {
      render(<FileTree {...defaultProps} />, { wrapper: createWrapper() });

      // Click the "src" directory to expand it
      fireEvent.click(screen.getByText("src"));

      // Children should now be visible
      expect(screen.getByText("index.ts")).toBeInTheDocument();
      expect(screen.getByText("utils")).toBeInTheDocument();
    });

    it("clicking an expanded directory collapses it", () => {
      render(<FileTree {...defaultProps} />, { wrapper: createWrapper() });

      // Expand "src"
      fireEvent.click(screen.getByText("src"));
      expect(screen.getByText("index.ts")).toBeInTheDocument();

      // Collapse "src"
      fireEvent.click(screen.getByText("src"));
      expect(screen.queryByText("index.ts")).not.toBeInTheDocument();
    });

    it("expanded directory children are sorted (directories before files)", () => {
      render(<FileTree {...defaultProps} />, { wrapper: createWrapper() });

      // Expand "src" which has: index.ts (file) and utils (directory)
      fireEvent.click(screen.getByText("src"));

      const treeItems = screen.getAllByRole("treeitem");
      // Find the items within the expanded src directory
      const srcIndex = treeItems.findIndex((item) => item.textContent?.includes("src"));
      // After src: utils (dir) should come before index.ts (file)
      expect(treeItems[srcIndex + 1]).toHaveTextContent("utils");
      expect(treeItems[srcIndex + 2]).toHaveTextContent("index.ts");
    });
  });

  describe("File selection", () => {
    it("clicking a file calls onFileSelect with the file's id", () => {
      const onFileSelect = vi.fn();
      mockTreeReturn = {
        data: sampleTree,
        isLoading: false,
        isError: false,
        error: null,
        refetch: mockRefetch,
      };

      render(
        <FileTree {...defaultProps} onFileSelect={onFileSelect} />,
        { wrapper: createWrapper() }
      );

      // Click on "alpha.ts" which has id: 2
      fireEvent.click(screen.getByText("alpha.ts"));
      expect(onFileSelect).toHaveBeenCalledWith(2);
    });

    it("clicking a directory does not call onFileSelect", () => {
      const onFileSelect = vi.fn();
      mockTreeReturn = {
        data: sampleTree,
        isLoading: false,
        isError: false,
        error: null,
        refetch: mockRefetch,
      };

      render(
        <FileTree {...defaultProps} onFileSelect={onFileSelect} />,
        { wrapper: createWrapper() }
      );

      fireEvent.click(screen.getByText("src"));
      expect(onFileSelect).not.toHaveBeenCalled();
    });
  });
});
