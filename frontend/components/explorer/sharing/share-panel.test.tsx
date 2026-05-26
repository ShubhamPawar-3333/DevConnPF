import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SharePanel } from "./share-panel";
import type { ShareInfo } from "@/lib/types/api";

// Mock the sharing hooks
const mockEnableMutate = vi.fn();
const mockDisableMutate = vi.fn();
const mockRegenerateMutate = vi.fn();

vi.mock("@/lib/hooks/use-sharing", () => ({
  useEnableSharing: () => ({
    mutate: mockEnableMutate,
    isPending: false,
  }),
  useDisableSharing: () => ({
    mutate: mockDisableMutate,
    isPending: false,
  }),
  useRegenerateShareUrl: () => ({
    mutate: mockRegenerateMutate,
    isPending: false,
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

const activeShareInfo: ShareInfo = {
  token: "abc123",
  url: "https://devconn.app/shared/abc123",
  isActive: true,
  createdAt: "2024-01-01T00:00:00Z",
};

describe("SharePanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders with sharing disabled when currentShareInfo is null", () => {
    render(<SharePanel repoId={1} currentShareInfo={null} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Public Sharing")).toBeInTheDocument();
    expect(screen.getByLabelText("Toggle public sharing")).not.toBeChecked();
    expect(screen.queryByLabelText("Share URL")).not.toBeInTheDocument();
  });

  it("renders with sharing enabled and shows URL when active", () => {
    render(<SharePanel repoId={1} currentShareInfo={activeShareInfo} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByLabelText("Toggle public sharing")).toBeChecked();
    expect(screen.getByLabelText("Share URL")).toHaveValue(
      "https://devconn.app/shared/abc123"
    );
    expect(screen.getByLabelText("Copy share URL")).toBeInTheDocument();
    expect(screen.getByText("Regenerate URL")).toBeInTheDocument();
  });

  it("calls enableSharing when toggle is switched on", () => {
    render(<SharePanel repoId={1} currentShareInfo={null} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByLabelText("Toggle public sharing"));
    expect(mockEnableMutate).toHaveBeenCalled();
  });

  it("calls disableSharing when toggle is switched off", () => {
    render(<SharePanel repoId={1} currentShareInfo={activeShareInfo} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByLabelText("Toggle public sharing"));
    expect(mockDisableMutate).toHaveBeenCalled();
  });

  it("copies URL to clipboard and shows confirmation for 3 seconds", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });

    render(<SharePanel repoId={1} currentShareInfo={activeShareInfo} />, {
      wrapper: createWrapper(),
    });

    await act(async () => {
      fireEvent.click(screen.getByLabelText("Copy share URL"));
    });

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      "https://devconn.app/shared/abc123"
    );

    expect(screen.getByText("Copied!")).toBeInTheDocument();
    expect(screen.getByLabelText("Copied")).toBeInTheDocument();

    // After 3 seconds, confirmation should disappear
    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.queryByText("Copied!")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Copy share URL")).toBeInTheDocument();

    vi.useRealTimers();
  });

  it("shows regenerate confirmation dialog when clicking Regenerate URL", () => {
    render(<SharePanel repoId={1} currentShareInfo={activeShareInfo} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByText("Regenerate URL"));

    expect(screen.getByText("Regenerate Share URL")).toBeInTheDocument();
    expect(
      screen.getByText(/The previous URL will stop working/)
    ).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Regenerate" })).toBeInTheDocument();
  });

  it("calls regenerateUrl when confirming regeneration", () => {
    render(<SharePanel repoId={1} currentShareInfo={activeShareInfo} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByText("Regenerate URL"));
    fireEvent.click(screen.getByRole("button", { name: "Regenerate" }));

    expect(mockRegenerateMutate).toHaveBeenCalled();
  });

  it("closes dialog when clicking Cancel", () => {
    render(<SharePanel repoId={1} currentShareInfo={activeShareInfo} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByText("Regenerate URL"));
    expect(screen.getByText("Regenerate Share URL")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Cancel"));

    waitFor(() => {
      expect(screen.queryByText("Regenerate Share URL")).not.toBeInTheDocument();
    });
  });

  it("displays error message when enable sharing fails", () => {
    mockEnableMutate.mockImplementation((_: unknown, options: { onError: (err: Error) => void }) => {
      options.onError(new Error("Network error"));
    });

    render(<SharePanel repoId={1} currentShareInfo={null} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByLabelText("Toggle public sharing"));

    expect(screen.getByRole("alert")).toHaveTextContent("Network error");
  });

  it("displays error message when regenerate fails", () => {
    mockRegenerateMutate.mockImplementation((_: unknown, options: { onError: (err: Error) => void }) => {
      options.onError(new Error("Server error"));
    });

    render(<SharePanel repoId={1} currentShareInfo={activeShareInfo} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByText("Regenerate URL"));
    fireEvent.click(screen.getByRole("button", { name: "Regenerate" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Server error");
  });

  it("has accessible labels for all interactive elements", () => {
    render(<SharePanel repoId={1} currentShareInfo={activeShareInfo} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByLabelText("Toggle public sharing")).toBeInTheDocument();
    expect(screen.getByLabelText("Share URL")).toBeInTheDocument();
    expect(screen.getByLabelText("Copy share URL")).toBeInTheDocument();
  });
});
