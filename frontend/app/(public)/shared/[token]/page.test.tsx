import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import SharedViewPage from "./page";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useParams: () => ({ token: "test-token-123" }),
}));

// Mock hooks
const mockSharedRepoData = {
  repository_id: 1,
  repository_name: "my-awesome-repo",
  status: "ready",
  owner_username: "johndoe",
  attribution: "Shared by johndoe",
  search_enabled: true,
  read_only: true,
  tree: [
    {
      id: 1,
      name: "src",
      path: "src",
      type: "directory" as const,
      language: null,
      summaryPreview: null,
      summaryStatus: "not_applicable" as const,
      children: [
        {
          id: 2,
          name: "index.ts",
          path: "src/index.ts",
          type: "file" as const,
          language: "typescript",
          summaryPreview: "Main entry point for the application",
          summaryStatus: "completed" as const,
          children: null,
        },
      ],
    },
    {
      id: 3,
      name: "README.md",
      path: "README.md",
      type: "file" as const,
      language: "markdown",
      summaryPreview: "Project documentation",
      summaryStatus: "completed" as const,
      children: null,
    },
  ],
  branding: "Powered by DevConnPf",
};

let mockSharedRepoReturn: {
  data: typeof mockSharedRepoData | undefined;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
};

let mockSearchReturn: {
  data: unknown[] | undefined;
  isLoading: boolean;
  isError: boolean;
};

vi.mock("@/lib/hooks/use-shared-repository", () => ({
  useSharedRepository: () => mockSharedRepoReturn,
}));

vi.mock("@/lib/hooks/use-shared-search", () => ({
  useSharedSearch: () => mockSearchReturn,
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("SharedViewPage", () => {
  beforeEach(() => {
    mockSharedRepoReturn = {
      data: mockSharedRepoData,
      isLoading: false,
      isError: false,
      error: null,
    };
    mockSearchReturn = {
      data: undefined,
      isLoading: false,
      isError: false,
    };
  });

  it("displays the attribution banner with owner username", () => {
    render(<SharedViewPage />, { wrapper: createWrapper() });

    expect(screen.getByText("johndoe")).toBeInTheDocument();
    expect(screen.getByText(/Shared by/)).toBeInTheDocument();
  });

  it("displays the repository name", () => {
    render(<SharedViewPage />, { wrapper: createWrapper() });

    expect(screen.getByText("my-awesome-repo")).toBeInTheDocument();
  });

  it("displays 'Powered by DevConn' watermark", () => {
    render(<SharedViewPage />, { wrapper: createWrapper() });

    expect(screen.getByText("Powered by DevConn")).toBeInTheDocument();
  });

  it("displays the file tree in read-only mode", () => {
    render(<SharedViewPage />, { wrapper: createWrapper() });

    expect(screen.getByRole("tree", { name: "File tree" })).toBeInTheDocument();
    expect(screen.getByText("src")).toBeInTheDocument();
    expect(screen.getByText("README.md")).toBeInTheDocument();
  });

  it("shows 404 message for invalid/expired tokens", () => {
    mockSharedRepoReturn = {
      data: undefined,
      isLoading: false,
      isError: true,
      error: { status: 404, message: "Not found" },
    };

    render(<SharedViewPage />, { wrapper: createWrapper() });

    expect(
      screen.getByText("This shared repository is no longer available.")
    ).toBeInTheDocument();
  });

  it("shows loading skeleton while fetching", () => {
    mockSharedRepoReturn = {
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    };

    render(<SharedViewPage />, { wrapper: createWrapper() });

    // Should show skeleton elements
    const skeletons = document.querySelectorAll('[class*="animate-pulse"], [data-slot="skeleton"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("has a search input for searching summaries", () => {
    render(<SharedViewPage />, { wrapper: createWrapper() });

    expect(screen.getByLabelText("Search summaries")).toBeInTheDocument();
  });

  it("does not show any edit/delete/manage controls", () => {
    render(<SharedViewPage />, { wrapper: createWrapper() });

    // No sharing toggle, no ingestion controls, no settings
    expect(screen.queryByText("Enable public access")).not.toBeInTheDocument();
    expect(screen.queryByText("Delete")).not.toBeInTheDocument();
    expect(screen.queryByText("Settings")).not.toBeInTheDocument();
    expect(screen.queryByText("Ingest")).not.toBeInTheDocument();
    expect(screen.queryByText("Regenerate")).not.toBeInTheDocument();
  });

  it("allows expanding/collapsing directories", () => {
    render(<SharedViewPage />, { wrapper: createWrapper() });

    // Initially, src directory is collapsed, so index.ts should not be visible
    expect(screen.queryByText("index.ts")).not.toBeInTheDocument();

    // Click to expand the src directory
    const expandButton = screen.getByLabelText("Expand");
    fireEvent.click(expandButton);

    // Now index.ts should be visible
    expect(screen.getByText("index.ts")).toBeInTheDocument();
  });

  it("shows 'Read-only view' label", () => {
    render(<SharedViewPage />, { wrapper: createWrapper() });

    expect(screen.getByText("Read-only view")).toBeInTheDocument();
  });

  it("shows search validation message for short queries", () => {
    render(<SharedViewPage />, { wrapper: createWrapper() });

    const searchInput = screen.getByLabelText("Search summaries");
    fireEvent.change(searchInput, { target: { value: "ab" } });

    expect(
      screen.getByText("Type at least 3 characters to search")
    ).toBeInTheDocument();
  });

  it("handles generic errors gracefully", () => {
    mockSharedRepoReturn = {
      data: undefined,
      isLoading: false,
      isError: true,
      error: { status: 500, message: "Internal server error" },
    };

    render(<SharedViewPage />, { wrapper: createWrapper() });

    expect(
      screen.getByText("Something went wrong loading this shared repository.")
    ).toBeInTheDocument();
  });
});
