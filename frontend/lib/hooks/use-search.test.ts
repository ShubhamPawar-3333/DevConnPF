import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import { useSearch } from "./use-search";
import { apiClient } from "@/lib/api/client";
import type { SearchResult } from "@/lib/types/api";

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

describe("useSearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not execute search for queries shorter than 3 chars", () => {
    renderHook(() => useSearch(1, "ab"), {
      wrapper: createWrapper(),
    });

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(apiClient.get).not.toHaveBeenCalled();
  });

  it("does not execute search for empty query", () => {
    renderHook(() => useSearch(1, ""), {
      wrapper: createWrapper(),
    });

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(apiClient.get).not.toHaveBeenCalled();
  });

  it("executes search for valid query after debounce", async () => {
    vi.useRealTimers();

    const mockResults: SearchResult[] = [
      {
        filePath: "src/auth.ts",
        blockName: "login",
        summaryExcerpt: "Handles user authentication",
        similarityRank: 0.95,
        resultType: "block",
        fileId: 1,
        blockId: 2,
      },
    ];

    vi.mocked(apiClient.get).mockResolvedValue(mockResults);

    const { result } = renderHook(() => useSearch(1, "authentication"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), {
      timeout: 1000,
    });

    expect(apiClient.get).toHaveBeenCalledWith(
      "/api/repositories/1/search/",
      { q: "authentication" }
    );
    expect(result.current.data).toEqual(mockResults);
  });

  it("does not execute search for queries longer than 300 chars", () => {
    const longQuery = "a".repeat(301);

    renderHook(() => useSearch(1, longQuery), {
      wrapper: createWrapper(),
    });

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(apiClient.get).not.toHaveBeenCalled();
  });
});
