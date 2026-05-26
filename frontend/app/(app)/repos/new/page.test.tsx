import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import NewRepoPage from "./page";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock API client
vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock ProgressPanel to simplify testing
vi.mock("@/components/explorer/progress/progress-panel", () => ({
  ProgressPanel: ({ repoId, onComplete }: { repoId: number; onComplete: () => void }) => (
    <div data-testid="progress-panel" data-repo-id={repoId}>
      <button onClick={onComplete} data-testid="simulate-complete">
        Complete
      </button>
    </div>
  ),
}));

import { apiClient } from "@/lib/api/client";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("NewRepoPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPush.mockClear();
  });

  it("shows loading skeleton while fetching repos", () => {
    // Never resolve the query
    (apiClient.get as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

    render(<NewRepoPage />, { wrapper: createWrapper() });

    expect(screen.getByText("Ingest Repository")).toBeInTheDocument();
  });

  it("shows ingestion form when under repo limit", async () => {
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValue([
      { id: 1, name: "repo-1", sourceType: "github" },
    ]);

    render(<NewRepoPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("GitHub URL")).toBeInTheDocument();
    });

    expect(screen.getByText("ZIP Upload")).toBeInTheDocument();
    expect(screen.getByLabelText("GitHub Repository URL")).toBeInTheDocument();
    expect(screen.getByText("Start Ingestion")).toBeInTheDocument();
  });

  it("shows limit reached message when at max repos", async () => {
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValue([
      { id: 1, name: "repo-1", sourceType: "github" },
      { id: 2, name: "repo-2", sourceType: "zip" },
      { id: 3, name: "repo-3", sourceType: "github" },
    ]);

    render(<NewRepoPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(
        screen.getByText(
          "You've reached the maximum of 3 repositories. Delete one to add a new repository."
        )
      ).toBeInTheDocument();
    });

    expect(screen.getByText("repo-1")).toBeInTheDocument();
    expect(screen.getByText("repo-2")).toBeInTheDocument();
    expect(screen.getByText("repo-3")).toBeInTheDocument();
  });

  it("disables submit button for invalid GitHub URL", async () => {
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValue([]);

    render(<NewRepoPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Start Ingestion")).toBeInTheDocument();
    });

    const input = screen.getByLabelText("GitHub Repository URL");
    fireEvent.change(input, { target: { value: "not-a-url" } });

    expect(screen.getByText("Start Ingestion")).toBeDisabled();
  });

  it("enables submit button for valid GitHub URL", async () => {
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValue([]);

    render(<NewRepoPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Start Ingestion")).toBeInTheDocument();
    });

    const input = screen.getByLabelText("GitHub Repository URL");
    fireEvent.change(input, { target: { value: "https://github.com/owner/repo" } });

    expect(screen.getByText("Start Ingestion")).not.toBeDisabled();
  });

  it("shows ProgressPanel after successful ingestion", async () => {
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      repository_id: 42,
    });

    render(<NewRepoPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Start Ingestion")).toBeInTheDocument();
    });

    const input = screen.getByLabelText("GitHub Repository URL");
    fireEvent.change(input, { target: { value: "https://github.com/owner/repo" } });
    fireEvent.click(screen.getByText("Start Ingestion"));

    await waitFor(() => {
      expect(screen.getByTestId("progress-panel")).toBeInTheDocument();
    });

    expect(screen.getByTestId("progress-panel")).toHaveAttribute(
      "data-repo-id",
      "42"
    );
  });

  it("navigates to tree view on progress complete", async () => {
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      repository_id: 42,
    });

    render(<NewRepoPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Start Ingestion")).toBeInTheDocument();
    });

    const input = screen.getByLabelText("GitHub Repository URL");
    fireEvent.change(input, { target: { value: "https://github.com/owner/repo" } });
    fireEvent.click(screen.getByText("Start Ingestion"));

    await waitFor(() => {
      expect(screen.getByTestId("progress-panel")).toBeInTheDocument();
    });

    // Simulate progress completion
    fireEvent.click(screen.getByTestId("simulate-complete"));

    expect(mockPush).toHaveBeenCalledWith("/repos/42/tree");
  });

  it("shows error message on ingestion failure", async () => {
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    (apiClient.post as ReturnType<typeof vi.fn>).mockRejectedValue({
      message: "Repository already exists",
      status: 409,
    });

    render(<NewRepoPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Start Ingestion")).toBeInTheDocument();
    });

    const input = screen.getByLabelText("GitHub Repository URL");
    fireEvent.change(input, { target: { value: "https://github.com/owner/repo" } });
    fireEvent.click(screen.getByText("Start Ingestion"));

    await waitFor(() => {
      expect(screen.getByText("Repository already exists")).toBeInTheDocument();
    });
  });

  it("shows retry option for server errors", async () => {
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    (apiClient.post as ReturnType<typeof vi.fn>).mockRejectedValue({
      message: "Internal server error",
      status: 500,
    });

    render(<NewRepoPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Start Ingestion")).toBeInTheDocument();
    });

    const input = screen.getByLabelText("GitHub Repository URL");
    fireEvent.change(input, { target: { value: "https://github.com/owner/repo" } });
    fireEvent.click(screen.getByText("Start Ingestion"));

    await waitFor(() => {
      expect(
        screen.getByText("This may be a temporary issue. You can try again.")
      ).toBeInTheDocument();
    });

    expect(screen.getByText("Retry")).toBeInTheDocument();
  });
});
