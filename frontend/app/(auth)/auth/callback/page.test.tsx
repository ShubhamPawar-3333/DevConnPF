import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import AuthCallbackPage from "./page";

// Mock next/navigation
const mockReplace = vi.fn();
let mockSearchParams: URLSearchParams;

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  useSearchParams: () => mockSearchParams,
}));

// Mock auth-guard
vi.mock("@/lib/auth/auth-guard", () => ({
  getPostLoginRedirectUrl: () => null,
}));

describe("AuthCallbackPage", () => {
  beforeEach(() => {
    mockReplace.mockClear();
    mockSearchParams = new URLSearchParams();
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows loading state while processing", async () => {
    mockSearchParams.set("code", "test-code");
    mockSearchParams.set("state", "test-state");

    // Never resolving fetch to keep the loading state
    (global.fetch as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise(() => {})
    );

    render(<AuthCallbackPage />);

    expect(screen.getByText("Signing you in...")).toBeInTheDocument();
  });

  it("redirects to error page when GitHub returns an error", () => {
    mockSearchParams.set("error", "access_denied");

    render(<AuthCallbackPage />);

    expect(mockReplace).toHaveBeenCalledWith(
      "/auth/error?error=access_denied"
    );
  });

  it("redirects to error page when no code is present", () => {
    render(<AuthCallbackPage />);

    expect(mockReplace).toHaveBeenCalledWith("/auth/error?error=missing_code");
  });

  it("exchanges code and shows success on valid response", async () => {
    mockSearchParams.set("code", "valid-code");
    mockSearchParams.set("state", "csrf-state");

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ user: { id: 1, username: "testuser" } }),
    });

    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/auth/github/callback/",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ code: "valid-code", state: "csrf-state" }),
        })
      );
    });

    // Show success state
    await waitFor(() => {
      expect(
        screen.getByText("Authentication successful")
      ).toBeInTheDocument();
    });
  });

  it("redirects to dashboard after successful auth", async () => {
    vi.useFakeTimers();

    mockSearchParams.set("code", "valid-code");
    mockSearchParams.set("state", "csrf-state");

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ user: { id: 1, username: "testuser" } }),
    });

    await act(async () => {
      render(<AuthCallbackPage />);
    });

    // Wait for the fetch to complete and state to update
    await act(async () => {
      await Promise.resolve();
    });

    // Advance timer to trigger redirect
    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(mockReplace).toHaveBeenCalledWith("/dashboard");

    vi.useRealTimers();
  });

  it("redirects to error page on API failure", async () => {
    mockSearchParams.set("code", "invalid-code");
    mockSearchParams.set("state", "csrf-state");

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 400,
      json: () => Promise.resolve({ error: "invalid_code" }),
    });

    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith(
        "/auth/error?error=invalid_code"
      );
    });
  });

  it("redirects to error page on network failure", async () => {
    mockSearchParams.set("code", "valid-code");
    mockSearchParams.set("state", "csrf-state");

    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("Network error")
    );

    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith(
        "/auth/error?error=network_error"
      );
    });
  });
});
