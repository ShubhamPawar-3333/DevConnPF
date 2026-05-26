import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SearchPanel } from "./search-panel";
import type { SearchResult } from "@/lib/types/api";

// Mock the useSearch hook
const mockUseSearch = vi.fn();
vi.mock("@/lib/hooks/use-search", () => ({
  useSearch: (...args: unknown[]) => mockUseSearch(...args),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

const mockResults: SearchResult[] = [
  {
    filePath: "src/auth/login.ts",
    blockName: "handleLogin",
    summaryExcerpt: "Handles user authentication via OAuth flow",
    similarityRank: 0.95,
    resultType: "block",
    fileId: 1,
    blockId: 10,
  },
  {
    filePath: "src/utils/helpers.ts",
    blockName: null,
    summaryExcerpt: "Utility functions for string manipulation",
    similarityRank: 0.82,
    resultType: "file",
    fileId: 2,
    blockId: null,
  },
];

describe("SearchPanel", () => {
  const mockOnResultSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Default: no results, not loading, no error
    mockUseSearch.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    });
  });

  it("shows 'Type at least 3 characters to search' when query is 1-2 chars", () => {
    render(
      <SearchPanel repoId={1} onResultSelect={mockOnResultSelect} />,
      { wrapper: createWrapper() }
    );

    const input = screen.getByLabelText("Search summaries");
    fireEvent.change(input, { target: { value: "ab" } });

    expect(
      screen.getByText("Type at least 3 characters to search")
    ).toBeInTheDocument();
  });

  it("shows 'Query must be 300 characters or less' when query exceeds 300 chars", () => {
    render(
      <SearchPanel repoId={1} onResultSelect={mockOnResultSelect} />,
      { wrapper: createWrapper() }
    );

    const input = screen.getByLabelText("Search summaries");
    const longQuery = "a".repeat(301);
    fireEvent.change(input, { target: { value: longQuery } });

    expect(
      screen.getByText("Query must be 300 characters or less")
    ).toBeInTheDocument();
  });

  it("does not show validation message when query is empty", () => {
    render(
      <SearchPanel repoId={1} onResultSelect={mockOnResultSelect} />,
      { wrapper: createWrapper() }
    );

    expect(
      screen.queryByText("Type at least 3 characters to search")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Query must be 300 characters or less")
    ).not.toBeInTheDocument();
  });

  it("shows loading skeletons while searching", () => {
    mockUseSearch.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });

    render(
      <SearchPanel repoId={1} onResultSelect={mockOnResultSelect} />,
      { wrapper: createWrapper() }
    );

    // Type a valid query so the component considers it valid
    const input = screen.getByLabelText("Search summaries");
    fireEvent.change(input, { target: { value: "auth login" } });

    expect(screen.getByLabelText("Loading search results")).toBeInTheDocument();
  });

  it("shows 'No matches found. Try different keywords.' when results are empty", () => {
    mockUseSearch.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    });

    render(
      <SearchPanel repoId={1} onResultSelect={mockOnResultSelect} />,
      { wrapper: createWrapper() }
    );

    // Type a valid query so hasValidQuery is true
    const input = screen.getByLabelText("Search summaries");
    fireEvent.change(input, { target: { value: "something" } });

    expect(
      screen.getByText("No matches found. Try different keywords.")
    ).toBeInTheDocument();
  });

  it("renders search results with file path and block name", () => {
    mockUseSearch.mockReturnValue({
      data: mockResults,
      isLoading: false,
      isError: false,
    });

    render(
      <SearchPanel repoId={1} onResultSelect={mockOnResultSelect} />,
      { wrapper: createWrapper() }
    );

    // Type a valid query
    const input = screen.getByLabelText("Search summaries");
    fireEvent.change(input, { target: { value: "auth" } });

    expect(screen.getByText("src/auth/login.ts")).toBeInTheDocument();
    expect(screen.getByText("handleLogin")).toBeInTheDocument();
    expect(screen.getByText("src/utils/helpers.ts")).toBeInTheDocument();
  });

  it("calls onResultSelect when clicking a result", () => {
    mockUseSearch.mockReturnValue({
      data: mockResults,
      isLoading: false,
      isError: false,
    });

    render(
      <SearchPanel repoId={1} onResultSelect={mockOnResultSelect} />,
      { wrapper: createWrapper() }
    );

    // Type a valid query
    const input = screen.getByLabelText("Search summaries");
    fireEvent.change(input, { target: { value: "auth" } });

    // Click the first result
    const firstResult = screen.getByLabelText(
      "View block: src/auth/login.ts - handleLogin"
    );
    fireEvent.click(firstResult);

    expect(mockOnResultSelect).toHaveBeenCalledWith(mockResults[0]);
  });

  it("shows error state when search fails", () => {
    mockUseSearch.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });

    render(
      <SearchPanel repoId={1} onResultSelect={mockOnResultSelect} />,
      { wrapper: createWrapper() }
    );

    expect(
      screen.getByText("Search could not be completed")
    ).toBeInTheDocument();
  });

  it("preserves query text in input on error", () => {
    mockUseSearch.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });

    render(
      <SearchPanel repoId={1} onResultSelect={mockOnResultSelect} />,
      { wrapper: createWrapper() }
    );

    const input = screen.getByLabelText("Search summaries");
    fireEvent.change(input, { target: { value: "my search query" } });

    // Input should still have the query text
    expect(input).toHaveValue("my search query");
    // Error should also be visible
    expect(
      screen.getByText("Search could not be completed")
    ).toBeInTheDocument();
  });
});
