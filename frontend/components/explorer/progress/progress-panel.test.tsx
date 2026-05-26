import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProgressPanel } from "./progress-panel";
import type { ProgressReport, RepositoryStatus } from "@/lib/types/api";

// Mock the useRepositoryProgress hook
let mockHookReturn: {
  data: ProgressReport | undefined;
  isError: boolean;
  isSuccess: boolean;
  dataUpdatedAt: number;
};

vi.mock("@/lib/hooks/use-repository-progress", () => ({
  useRepositoryProgress: () => mockHookReturn,
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

function makeProgress(overrides: Partial<ProgressReport> = {}): ProgressReport {
  return {
    totalJobs: 10,
    completed: 5,
    pending: 3,
    failed: 2,
    status: "summarizing",
    ...overrides,
  };
}

describe("ProgressPanel", () => {
  let onComplete: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onComplete = vi.fn();
    mockHookReturn = {
      data: undefined,
      isError: false,
      isSuccess: false,
      dataUpdatedAt: Date.now(),
    };
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("indeterminate state", () => {
    it("shows indeterminate state when totalJobs is 0", () => {
      mockHookReturn = {
        data: makeProgress({ totalJobs: 0, completed: 0, pending: 0, failed: 0 }),
        isError: false,
        isSuccess: true,
        dataUpdatedAt: Date.now(),
      };

      render(<ProgressPanel repoId={1} onComplete={onComplete} />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText("Preparing...")).toBeInTheDocument();
      expect(
        screen.getByLabelText("Progress: indeterminate")
      ).toBeInTheDocument();
    });

    it("shows indeterminate state when progress data is undefined", () => {
      mockHookReturn = {
        data: undefined,
        isError: false,
        isSuccess: false,
        dataUpdatedAt: Date.now(),
      };

      render(<ProgressPanel repoId={1} onComplete={onComplete} />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText("Preparing...")).toBeInTheDocument();
      expect(
        screen.getByLabelText("Progress: indeterminate")
      ).toBeInTheDocument();
    });
  });

  describe("progress percentage calculation", () => {
    it("shows correct percentage for 5/10 completed (50%)", () => {
      mockHookReturn = {
        data: makeProgress({ totalJobs: 10, completed: 5 }),
        isError: false,
        isSuccess: true,
        dataUpdatedAt: Date.now(),
      };

      render(<ProgressPanel repoId={1} onComplete={onComplete} />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText("50%")).toBeInTheDocument();
      expect(screen.getByLabelText("Progress: 50%")).toBeInTheDocument();
    });

    it("shows 0% when no jobs are completed", () => {
      mockHookReturn = {
        data: makeProgress({ totalJobs: 10, completed: 0 }),
        isError: false,
        isSuccess: true,
        dataUpdatedAt: Date.now(),
      };

      render(<ProgressPanel repoId={1} onComplete={onComplete} />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText("0%")).toBeInTheDocument();
    });

    it("shows 100% when all jobs are completed", () => {
      mockHookReturn = {
        data: makeProgress({ totalJobs: 10, completed: 10, pending: 0, failed: 0 }),
        isError: false,
        isSuccess: true,
        dataUpdatedAt: Date.now(),
      };

      render(<ProgressPanel repoId={1} onComplete={onComplete} />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText("100%")).toBeInTheDocument();
    });
  });

  describe("job counts display", () => {
    it("shows completed, pending, and failed counts", () => {
      mockHookReturn = {
        data: makeProgress({ completed: 5, pending: 3, failed: 2 }),
        isError: false,
        isSuccess: true,
        dataUpdatedAt: Date.now(),
      };

      render(<ProgressPanel repoId={1} onComplete={onComplete} />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText("5 completed")).toBeInTheDocument();
      expect(screen.getByText("3 pending")).toBeInTheDocument();
      expect(screen.getByText("2 failed")).toBeInTheDocument();
    });

    it("hides failed count when there are no failures", () => {
      mockHookReturn = {
        data: makeProgress({ completed: 7, pending: 3, failed: 0 }),
        isError: false,
        isSuccess: true,
        dataUpdatedAt: Date.now(),
      };

      render(<ProgressPanel repoId={1} onComplete={onComplete} />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText("7 completed")).toBeInTheDocument();
      expect(screen.getByText("3 pending")).toBeInTheDocument();
      expect(screen.queryByText(/failed/)).not.toBeInTheDocument();
    });
  });

  describe("terminal status and onComplete callback", () => {
    it("calls onComplete when status is 'ready'", () => {
      mockHookReturn = {
        data: makeProgress({ status: "ready", completed: 10, pending: 0, failed: 0 }),
        isError: false,
        isSuccess: true,
        dataUpdatedAt: Date.now(),
      };

      render(<ProgressPanel repoId={1} onComplete={onComplete} />, {
        wrapper: createWrapper(),
      });

      expect(onComplete).toHaveBeenCalledTimes(1);
    });

    it("calls onComplete when status is 'failed'", () => {
      mockHookReturn = {
        data: makeProgress({ status: "failed" }),
        isError: false,
        isSuccess: true,
        dataUpdatedAt: Date.now(),
      };

      render(<ProgressPanel repoId={1} onComplete={onComplete} />, {
        wrapper: createWrapper(),
      });

      expect(onComplete).toHaveBeenCalledTimes(1);
    });

    it("calls onComplete when status is 'partially_summarized'", () => {
      mockHookReturn = {
        data: makeProgress({ status: "partially_summarized" }),
        isError: false,
        isSuccess: true,
        dataUpdatedAt: Date.now(),
      };

      render(<ProgressPanel repoId={1} onComplete={onComplete} />, {
        wrapper: createWrapper(),
      });

      expect(onComplete).toHaveBeenCalledTimes(1);
    });

    it("does not call onComplete for non-terminal statuses", () => {
      mockHookReturn = {
        data: makeProgress({ status: "summarizing" }),
        isError: false,
        isSuccess: true,
        dataUpdatedAt: Date.now(),
      };

      render(<ProgressPanel repoId={1} onComplete={onComplete} />, {
        wrapper: createWrapper(),
      });

      expect(onComplete).not.toHaveBeenCalled();
    });
  });

  describe("warning banner on consecutive errors", () => {
    it("shows warning banner after 3 consecutive errors", () => {
      mockHookReturn = {
        data: undefined,
        isError: true,
        isSuccess: false,
        dataUpdatedAt: 1,
      };

      const { rerender } = render(
        <ProgressPanel repoId={1} onComplete={onComplete} />,
        { wrapper: createWrapper() }
      );

      // Simulate 2nd error with updated dataUpdatedAt
      mockHookReturn = { ...mockHookReturn, dataUpdatedAt: 2 };
      rerender(<ProgressPanel repoId={1} onComplete={onComplete} />);

      // Simulate 3rd error
      mockHookReturn = { ...mockHookReturn, dataUpdatedAt: 3 };
      rerender(<ProgressPanel repoId={1} onComplete={onComplete} />);

      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(
        screen.getByText(/Connectivity issue detected/)
      ).toBeInTheDocument();
    });

    it("does not show warning banner with fewer than 3 errors", () => {
      mockHookReturn = {
        data: undefined,
        isError: true,
        isSuccess: false,
        dataUpdatedAt: 1,
      };

      const { rerender } = render(
        <ProgressPanel repoId={1} onComplete={onComplete} />,
        { wrapper: createWrapper() }
      );

      // Only 2 errors
      mockHookReturn = { ...mockHookReturn, dataUpdatedAt: 2 };
      rerender(<ProgressPanel repoId={1} onComplete={onComplete} />);

      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("hides warning banner after successful response", () => {
      mockHookReturn = {
        data: undefined,
        isError: true,
        isSuccess: false,
        dataUpdatedAt: 1,
      };

      const { rerender } = render(
        <ProgressPanel repoId={1} onComplete={onComplete} />,
        { wrapper: createWrapper() }
      );

      // Trigger 3 errors
      mockHookReturn = { ...mockHookReturn, dataUpdatedAt: 2 };
      rerender(<ProgressPanel repoId={1} onComplete={onComplete} />);

      mockHookReturn = { ...mockHookReturn, dataUpdatedAt: 3 };
      rerender(<ProgressPanel repoId={1} onComplete={onComplete} />);

      // Verify banner is shown
      expect(screen.getByRole("alert")).toBeInTheDocument();

      // Simulate successful response
      mockHookReturn = {
        data: makeProgress({ status: "summarizing" }),
        isError: false,
        isSuccess: true,
        dataUpdatedAt: 4,
      };
      rerender(<ProgressPanel repoId={1} onComplete={onComplete} />);

      // Banner should be dismissed
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
  });

  describe("StatusBadge display", () => {
    const statusLabels: [RepositoryStatus, string][] = [
      ["cloning", "Cloning repository..."],
      ["extracting", "Extracting files..."],
      ["parsing", "Parsing code..."],
      ["summarizing", "Generating summaries..."],
      ["ready", "Complete"],
      ["partially_summarized", "Partially complete"],
      ["failed", "Failed"],
    ];

    it.each(statusLabels)(
      "shows StatusBadge with correct label for status '%s'",
      (status, expectedLabel) => {
        mockHookReturn = {
          data: makeProgress({ status }),
          isError: false,
          isSuccess: true,
          dataUpdatedAt: Date.now(),
        };

        render(<ProgressPanel repoId={1} onComplete={vi.fn()} />, {
          wrapper: createWrapper(),
        });

        expect(
          screen.getByLabelText(`Status: ${expectedLabel}`)
        ).toBeInTheDocument();
      }
    );
  });
});
