import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import SettingsPage from "./page";

// Mock auth context
const mockUser = {
  id: 1,
  username: "testuser",
  email: "test@example.com",
  languagePreference: "en" as const,
  avatarUrl: null,
};

vi.mock("@/lib/auth/auth-context", () => ({
  useAuth: () => ({
    user: mockUser,
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

// Mock language preference hook
const mockMutate = vi.fn();
let mockIsPending = false;

vi.mock("@/lib/hooks/use-language-preference", () => ({
  useUpdateLanguage: () => ({
    mutate: mockMutate,
    isPending: mockIsPending,
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

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsPending = false;
    mockUser.languagePreference = "en";
  });

  it("renders the settings page with language selector", () => {
    render(<SettingsPage />, { wrapper: createWrapper() });

    expect(screen.getByText("Settings")).toBeInTheDocument();
    expect(screen.getByText("Language Preference")).toBeInTheDocument();
    expect(screen.getByLabelText("Preferred Language")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
  });

  it("displays all 8 language options", () => {
    render(<SettingsPage />, { wrapper: createWrapper() });

    const select = screen.getByLabelText("Preferred Language") as HTMLSelectElement;
    const options = select.querySelectorAll("option");

    expect(options).toHaveLength(8);
    expect(options[0]).toHaveTextContent("English");
    expect(options[1]).toHaveTextContent("Spanish");
    expect(options[2]).toHaveTextContent("French");
    expect(options[3]).toHaveTextContent("German");
    expect(options[4]).toHaveTextContent("Portuguese");
    expect(options[5]).toHaveTextContent("Japanese");
    expect(options[6]).toHaveTextContent("Korean");
    expect(options[7]).toHaveTextContent("Chinese");
  });

  it("pre-selects the user's current language preference", () => {
    mockUser.languagePreference = "fr";
    render(<SettingsPage />, { wrapper: createWrapper() });

    const select = screen.getByLabelText("Preferred Language") as HTMLSelectElement;
    expect(select.value).toBe("fr");
  });

  it("calls updateLanguage mutation on save", () => {
    render(<SettingsPage />, { wrapper: createWrapper() });

    const select = screen.getByLabelText("Preferred Language");
    fireEvent.change(select, { target: { value: "ja" } });

    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(mockMutate).toHaveBeenCalledWith("ja", expect.objectContaining({
      onSuccess: expect.any(Function),
      onError: expect.any(Function),
    }));
  });

  it("shows success message on successful save", () => {
    mockMutate.mockImplementation((_, options) => {
      options.onSuccess();
    });

    render(<SettingsPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(screen.getByRole("status")).toHaveTextContent("Language preference saved");
  });

  it("shows error message and reverts selection on failure", () => {
    mockUser.languagePreference = "en";
    mockMutate.mockImplementation((_, options) => {
      options.onError(new Error("Network error"));
    });

    render(<SettingsPage />, { wrapper: createWrapper() });

    const select = screen.getByLabelText("Preferred Language") as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "ko" } });

    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Failed to save preference");
    // Should revert to original preference
    expect(select.value).toBe("en");
  });

  it("disables controls while saving", () => {
    mockIsPending = true;

    render(<SettingsPage />, { wrapper: createWrapper() });

    const select = screen.getByLabelText("Preferred Language");
    const button = screen.getByRole("button", { name: "Saving..." });

    expect(select).toBeDisabled();
    expect(button).toBeDisabled();
  });
});
