import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useLanguage } from "./use-language";

// Mock the auth context
const mockUseAuth = vi.fn();
vi.mock("@/lib/auth/auth-context", () => ({
  useAuth: () => mockUseAuth(),
}));

describe("useLanguage", () => {
  it("returns user's language preference when authenticated", () => {
    mockUseAuth.mockReturnValue({
      user: { id: 1, username: "test", email: "test@test.com", languagePreference: "ja", avatarUrl: null },
      isAuthenticated: true,
      isLoading: false,
    });

    const { result } = renderHook(() => useLanguage());
    expect(result.current).toBe("ja");
  });

  it("returns 'en' when user is not authenticated", () => {
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });

    const { result } = renderHook(() => useLanguage());
    expect(result.current).toBe("en");
  });

  it("returns 'en' when user has no language preference set", () => {
    mockUseAuth.mockReturnValue({
      user: { id: 1, username: "test", email: "test@test.com", languagePreference: undefined, avatarUrl: null },
      isAuthenticated: true,
      isLoading: false,
    });

    const { result } = renderHook(() => useLanguage());
    expect(result.current).toBe("en");
  });
});
