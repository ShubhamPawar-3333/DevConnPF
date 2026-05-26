import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { AuthContextProvider, useAuth } from "./auth-context";

// Helper component to consume auth context
function AuthConsumer() {
  const { user, isAuthenticated, isLoading } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="username">{user?.username ?? "none"}</span>
    </div>
  );
}

const mockUser = {
  id: 1,
  username: "testuser",
  email: "test@example.com",
  languagePreference: "en" as const,
  avatarUrl: null,
};

describe("AuthContextProvider", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts in loading state and resolves to authenticated when session is valid", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        isAuthenticated: true,
        user: mockUser,
      }),
    } as Response);

    render(
      <AuthContextProvider>
        <AuthConsumer />
      </AuthContextProvider>
    );

    // Initially loading
    expect(screen.getByTestId("loading").textContent).toBe("true");

    // After session check resolves
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("authenticated").textContent).toBe("true");
    expect(screen.getByTestId("username").textContent).toBe("testuser");
  });

  it("resolves to unauthenticated when session check returns anonymous session", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        isAuthenticated: false,
        user: null,
      }),
    } as Response);

    render(
      <AuthContextProvider>
        <AuthConsumer />
      </AuthContextProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("authenticated").textContent).toBe("false");
    expect(screen.getByTestId("username").textContent).toBe("none");
  });

  it("resolves to unauthenticated when session check throws", async () => {
    vi.spyOn(global, "fetch").mockRejectedValueOnce(new Error("Network error"));

    render(
      <AuthContextProvider>
        <AuthConsumer />
      </AuthContextProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("authenticated").textContent).toBe("false");
  });

  it("login redirects through Django social auth", async () => {
    const fetchMock = vi.spyOn(global, "fetch");
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        isAuthenticated: false,
        user: null,
      }),
    } as Response);

    const originalLocation = window.location;
    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...originalLocation, href: "" },
    });

    function LoginButton() {
      const { login } = useAuth();
      return <button onClick={login}>Login</button>;
    }

    render(
      <AuthContextProvider>
        <LoginButton />
      </AuthContextProvider>
    );

    await act(async () => {
      screen.getByText("Login").click();
    });

    await waitFor(() => {
      expect(window.location.href).toBe("/api/auth/github/");
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);

    Object.defineProperty(window, "location", {
      writable: true,
      value: originalLocation,
    });
  });

  it("logout calls POST /api/auth/logout/ and redirects to /login", async () => {
    const fetchMock = vi.spyOn(global, "fetch");
    // First call: session check
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        isAuthenticated: true,
        user: mockUser,
      }),
    } as Response);
    // Second call: logout
    fetchMock.mockResolvedValueOnce({
      ok: true,
    } as Response);

    const originalLocation = window.location;
    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...originalLocation, href: "" },
    });

    function LogoutButton() {
      const { logout } = useAuth();
      return <button onClick={logout}>Logout</button>;
    }

    render(
      <AuthContextProvider>
        <LogoutButton />
      </AuthContextProvider>
    );

    // Wait for session check to complete
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/auth/me/", expect.any(Object));
    });

    await act(async () => {
      screen.getByText("Logout").click();
    });

    // Verify logout was called with same-origin credentials and CSRF header
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/logout/", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": expect.any(String),
      },
    });
    expect(window.location.href).toBe("/login");

    Object.defineProperty(window, "location", {
      writable: true,
      value: originalLocation,
    });
  });

  it("throws error when useAuth is used outside provider", () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => {
      render(<AuthConsumer />);
    }).toThrow("useAuth must be used within an AuthContextProvider");

    consoleSpy.mockRestore();
  });
});
