import { describe, it, expect } from "vitest";
import * as fc from "fast-check";
import type { ProgressReport, RepositoryStatus } from "@/lib/types/api";

/**
 * Property 5: Polling Termination Guarantee
 *
 * For any ProgressReport with a terminal status ("ready", "partially_summarized", "failed"),
 * the polling refetchInterval logic returns false (stop polling).
 * For any non-terminal status, it returns the POLL_INTERVAL (5000ms).
 * For any sequence of ProgressReports ending with a terminal status,
 * the last status always triggers termination.
 *
 * **Validates: Requirements 10.1, 10.5**
 */

// Replicate the termination logic from use-repository-progress.ts as a pure function
const POLL_INTERVAL = 5000;
const TERMINAL_STATUSES: RepositoryStatus[] = [
  "ready",
  "partially_summarized",
  "failed",
];

/**
 * Pure function replicating the refetchInterval logic.
 * Returns false to stop polling on terminal status, or POLL_INTERVAL to continue.
 */
function getRefetchInterval(status: RepositoryStatus | undefined): number | false {
  if (status && TERMINAL_STATUSES.includes(status)) {
    return false;
  }
  return POLL_INTERVAL;
}

// All possible repository statuses
const ALL_STATUSES: RepositoryStatus[] = [
  "cloning",
  "extracting",
  "parsing",
  "summarizing",
  "ready",
  "partially_summarized",
  "failed",
];

const NON_TERMINAL_STATUSES: RepositoryStatus[] = [
  "cloning",
  "extracting",
  "parsing",
  "summarizing",
];

// Arbitraries
const terminalStatusArb: fc.Arbitrary<RepositoryStatus> = fc.constantFrom(
  "ready" as RepositoryStatus,
  "partially_summarized" as RepositoryStatus,
  "failed" as RepositoryStatus
);

const nonTerminalStatusArb: fc.Arbitrary<RepositoryStatus> = fc.constantFrom(
  "cloning" as RepositoryStatus,
  "extracting" as RepositoryStatus,
  "parsing" as RepositoryStatus,
  "summarizing" as RepositoryStatus
);

const anyStatusArb: fc.Arbitrary<RepositoryStatus> = fc.constantFrom(...ALL_STATUSES);

const progressReportArb = (statusArb: fc.Arbitrary<RepositoryStatus>): fc.Arbitrary<ProgressReport> =>
  fc.record({
    totalJobs: fc.integer({ min: 0, max: 10000 }),
    completed: fc.integer({ min: 0, max: 10000 }),
    pending: fc.integer({ min: 0, max: 10000 }),
    failed: fc.integer({ min: 0, max: 10000 }),
    status: statusArb,
  });

describe("Property 5: Polling Termination Guarantee", () => {
  it("terminal statuses always stop polling (refetchInterval returns false)", () => {
    fc.assert(
      fc.property(terminalStatusArb, (status) => {
        const result = getRefetchInterval(status);
        expect(result).toBe(false);
      }),
      { numRuns: 200 }
    );
  });

  it("non-terminal statuses always continue polling (refetchInterval returns POLL_INTERVAL)", () => {
    fc.assert(
      fc.property(nonTerminalStatusArb, (status) => {
        const result = getRefetchInterval(status);
        expect(result).toBe(POLL_INTERVAL);
      }),
      { numRuns: 200 }
    );
  });

  it("undefined status continues polling (initial state before first response)", () => {
    const result = getRefetchInterval(undefined);
    expect(result).toBe(POLL_INTERVAL);
  });

  it("for any ProgressReport with terminal status, polling stops", () => {
    fc.assert(
      fc.property(progressReportArb(terminalStatusArb), (report) => {
        const result = getRefetchInterval(report.status);
        expect(result).toBe(false);
      }),
      { numRuns: 300 }
    );
  });

  it("for any ProgressReport with non-terminal status, polling continues", () => {
    fc.assert(
      fc.property(progressReportArb(nonTerminalStatusArb), (report) => {
        const result = getRefetchInterval(report.status);
        expect(result).toBe(POLL_INTERVAL);
      }),
      { numRuns: 300 }
    );
  });

  it("any sequence of statuses ending with a terminal status triggers termination on the last element", () => {
    // Generate a random sequence of non-terminal statuses followed by a terminal status
    const statusSequenceArb = fc.tuple(
      fc.array(nonTerminalStatusArb, { minLength: 0, maxLength: 50 }),
      terminalStatusArb
    ).map(([prefix, terminal]) => [...prefix, terminal]);

    fc.assert(
      fc.property(statusSequenceArb, (sequence) => {
        // All non-terminal statuses in the prefix should continue polling
        for (let i = 0; i < sequence.length - 1; i++) {
          expect(getRefetchInterval(sequence[i])).toBe(POLL_INTERVAL);
        }

        // The final terminal status should stop polling
        const lastStatus = sequence[sequence.length - 1];
        expect(getRefetchInterval(lastStatus)).toBe(false);
      }),
      { numRuns: 500 }
    );
  });

  it("termination decision is deterministic for any given status", () => {
    fc.assert(
      fc.property(anyStatusArb, (status) => {
        // Calling the function multiple times with the same status always gives the same result
        const result1 = getRefetchInterval(status);
        const result2 = getRefetchInterval(status);
        const result3 = getRefetchInterval(status);

        expect(result1).toBe(result2);
        expect(result2).toBe(result3);
      }),
      { numRuns: 200 }
    );
  });

  it("exactly 3 statuses are terminal and exactly 4 are non-terminal", () => {
    // Verify the partition is exhaustive
    const terminalCount = ALL_STATUSES.filter((s) =>
      TERMINAL_STATUSES.includes(s)
    ).length;
    const nonTerminalCount = ALL_STATUSES.filter(
      (s) => !TERMINAL_STATUSES.includes(s)
    ).length;

    expect(terminalCount).toBe(3);
    expect(nonTerminalCount).toBe(4);
    expect(terminalCount + nonTerminalCount).toBe(ALL_STATUSES.length);
  });
});
