import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import {
  useEnableSharing,
  useDisableSharing,
  useRegenerateShareUrl,
} from "./use-sharing";
import { apiClient } from "@/lib/api/client";
import type { ShareInfo } from "@/lib/types/api";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("useEnableSharing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls enable sharing endpoint and returns share info", async () => {
    const mockShareInfo: ShareInfo = {
      token: "abc123",
      url: "https://app.devconn.io/shared/abc123",
      isActive: true,
      createdAt: "2024-01-01T00:00:00Z",
    };

    vi.mocked(apiClient.post).mockResolvedValue(mockShareInfo);

    const { result } = renderHook(() => useEnableSharing(1), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.post).toHaveBeenCalledWith(
      "/api/repositories/1/share/enable/"
    );
    expect(result.current.data).toEqual(mockShareInfo);
  });
});

describe("useDisableSharing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls disable sharing endpoint", async () => {
    vi.mocked(apiClient.post).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDisableSharing(1), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.post).toHaveBeenCalledWith(
      "/api/repositories/1/share/disable/"
    );
  });
});

describe("useRegenerateShareUrl", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls regenerate endpoint and returns new share info", async () => {
    const mockShareInfo: ShareInfo = {
      token: "new-token",
      url: "https://app.devconn.io/shared/new-token",
      isActive: true,
      createdAt: "2024-01-02T00:00:00Z",
    };

    vi.mocked(apiClient.post).mockResolvedValue(mockShareInfo);

    const { result } = renderHook(() => useRegenerateShareUrl(1), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.post).toHaveBeenCalledWith(
      "/api/repositories/1/share/regenerate/"
    );
    expect(result.current.data).toEqual(mockShareInfo);
  });
});
