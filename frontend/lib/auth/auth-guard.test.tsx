import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { AuthGuard, getPostLoginRedirectUrl } from "./auth-guard";

// Mock next/navigation
const mockReplace = vi.fn();
const mockPathname = "/dashboard";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: mockReplace,
    push: vi.fn(),
  }),
  usePathname: () => mockPathname,
}));

// Mock useAuth
const mockUseAuth = vi.fn();
vi.mock("./auth-context", () => ({
  useAuth: () => mockUseAuth(),
}));

describe("AuthGuard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders loading skeleton while auth is loading", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    });

    render(
      <AuthGuard>
        <div data-testid="protected-content">Protected</div>
      </AuthGuard>
    );

    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Loading")).toBeInTheDocument();
  });

  it("renders children when authenticated", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });

    render(
      <AuthGuard>
        <div data-testid="protected-content">Protected</div>
      </AuthGuard>
    );

    expect(screen.getByTestId("protected-content")).toBeInTheDocument();
  });

  it("redirects to /login when not authenticated", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    render(
      <AuthGuard>
        <div data-testid="protected-content">Protected</div>
      </AuthGuard>
    );

    expect(mockReplace).toHaveBeenCalledWith("/login");
    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
  });

  it("stores requested URL in sessionStorage when redirecting", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    render(
      <AuthGuard>
        <div>Protected</div>
      </AuthGuard>
    );

    expect(sessionStorage.getItem("auth_redirect_url")).toBe("/dashboard");
  });

  it("redirects to /login with error=timeout after 10 seconds", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    });

    render(
      <AuthGuard>
        <div data-testid="protected-content">Protected</div>
      </AuthGuard>
    );

    // Before timeout
    expect(mockReplace).not.toHaveBeenCalled();

    // Advance past timeout
    act(() => {
      vi.advanceTimersByTime(10_000);
    });

    expect(mockReplace).toHaveBeenCalledWith("/login?error=timeout");
    expect(sessionStorage.getItem("auth_redirect_url")).toBe("/dashboard");
  });

  it("does not redirect on timeout if auth resolves before 10s", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    });

    const { rerender } = render(
      <AuthGuard>
        <div data-testid="protected-content">Protected</div>
      </AuthGuard>
    );

    // Auth resolves as authenticated before timeout
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });

    rerender(
      <AuthGuard>
        <div data-testid="protected-content">Protected</div>
      </AuthGuard>
    );

    // Advance past timeout
    act(() => {
      vi.advanceTimersByTime(10_000);
    });

    // Should not have redirected with timeout error
    expect(mockReplace).not.toHaveBeenCalledWith("/login?error=timeout");
    expect(screen.getByTestId("protected-content")).toBeInTheDocument();
  });
});

describe("getPostLoginRedirectUrl", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("returns null when no redirect URL is stored", () => {
    expect(getPostLoginRedirectUrl()).toBeNull();
  });

  it("returns and clears the stored redirect URL", () => {
    sessionStorage.setItem("auth_redirect_url", "/repos/1/tree");

    const url = getPostLoginRedirectUrl();
    expect(url).toBe("/repos/1/tree");
    expect(sessionStorage.getItem("auth_redirect_url")).toBeNull();
  });
});
