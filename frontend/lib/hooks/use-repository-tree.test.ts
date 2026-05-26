import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import { useRepositoryTree } from "./use-repository-tree";
import { apiClient } from "@/lib/api/client";
import type { FileTreeNode } from "@/lib/types/api";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("useRepositoryTree", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches file tree for a valid repoId", async () => {
    const mockTree: FileTreeNode[] = [
      {
        id: 1,
        name: "src",
        path: "src",
        type: "directory",
        language: null,
        summaryPreview: null,
        summaryStatus: "not_applicable",
        children: [],
      },
    ];

    vi.mocked(apiClient.get).mockResolvedValue(mockTree);

    const { result } = renderHook(() => useRepositoryTree(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockTree);
    expect(apiClient.get).toHaveBeenCalledWith("/api/repositories/1/tree/");
  });

  it("does not fetch when repoId is 0", () => {
    renderHook(() => useRepositoryTree(0), {
      wrapper: createWrapper(),
    });

    expect(apiClient.get).not.toHaveBeenCalled();
  });
});
