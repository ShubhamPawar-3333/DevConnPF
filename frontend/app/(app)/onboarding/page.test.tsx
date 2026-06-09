/**
 * Task 21.2 — Page-level tests for the onboarding flow
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import OnboardingPage from "./page";

// Mock auth
vi.mock("@/lib/auth/auth-context", () => ({
  useAuth: () => ({
    user: { id: 1, username: "testuser", email: "test@example.com" },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

// Mock auth guard — just render children
vi.mock("@/lib/auth/auth-guard", () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock create profile mutation
const mockCreateProfile = vi.fn();
vi.mock("@/lib/hooks/use-profiles", () => ({
  useCreateProfile: () => ({
    mutate: mockCreateProfile,
    isPending: false,
    error: null,
  }),
}));

// Mock router
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("OnboardingPage", () => {
  beforeEach(() => mockCreateProfile.mockClear());

  it("renders step 1 with display name and slug fields", () => {
    render(<OnboardingPage />, { wrapper });
    expect(screen.getByLabelText(/display name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/profile slug/i)).toBeInTheDocument();
  });

  it("shows validation error when display name is too short", async () => {
    render(<OnboardingPage />, { wrapper });
    fireEvent.change(screen.getByLabelText(/display name/i), { target: { value: "A" } });
    fireEvent.change(screen.getByLabelText(/profile slug/i), { target: { value: "valid-slug" } });
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() => {
      expect(screen.getByText(/2.+100 characters/i)).toBeInTheDocument();
    });
  });

  it("advances to step 2 when step 1 is valid", async () => {
    render(<OnboardingPage />, { wrapper });
    fireEvent.change(screen.getByLabelText(/display name/i), { target: { value: "Jane Dev" } });
    fireEvent.change(screen.getByLabelText(/profile slug/i), { target: { value: "jane-dev" } });
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() => {
      expect(screen.getByLabelText(/bio/i)).toBeInTheDocument();
    });
  });
});
