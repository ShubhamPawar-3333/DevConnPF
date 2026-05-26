import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import { useRepositoryProgress } from "./use-repository-progress";
import { apiClient } from "@/lib/api/client";
import type { ProgressReport } from "@/lib/types/api";

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

describe("useRepositoryProgress", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches progress for a valid repoId", async () => {
    const mockProgress: ProgressReport = {
      totalJobs: 10,
      completed: 5,
      pending: 3,
      failed: 2,
      status: "summarizing",
    };

    vi.mocked(apiClient.get).mockResolvedValue(mockProgress);

    const { result } = renderHook(() => useRepositoryProgress(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockProgress);
    expect(apiClient.get).toHaveBeenCalledWith(
      "/api/repositories/1/progress/"
    );
  });

  it("does not fetch when repoId is 0", () => {
    renderHook(() => useRepositoryProgress(0), {
      wrapper: createWrapper(),
    });

    expect(apiClient.get).not.toHaveBeenCalled();
  });

  it("does not fetch when enabled is false", () => {
    renderHook(() => useRepositoryProgress(1, { enabled: false }), {
      wrapper: createWrapper(),
    });

    expect(apiClient.get).not.toHaveBeenCalled();
  });

  it("returns terminal status data correctly", async () => {
    const mockProgress: ProgressReport = {
      totalJobs: 10,
      completed: 10,
      pending: 0,
      failed: 0,
      status: "ready",
    };

    vi.mocked(apiClient.get).mockResolvedValue(mockProgress);

    const { result } = renderHook(() => useRepositoryProgress(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.status).toBe("ready");
  });
});
