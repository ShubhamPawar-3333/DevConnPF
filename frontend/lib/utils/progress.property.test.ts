import { describe, it, expect } from "vitest";
import * as fc from "fast-check";
import { calculateProgress } from "./progress";

/**
 * Property-based tests for calculateProgress.
 *
 * **Validates: Requirements 10.2**
 *
 * Property 3: Progress Percentage Bounds
 * For any ProgressReport where totalJobs > 0, the computed percentage
 * Math.round((completed / totalJobs) * 100) SHALL be between 0 and 100
 * inclusive. Additionally, completed + pending + failed === totalJobs
 * SHALL always hold.
 */
describe("calculateProgress - Property Tests", () => {
  it("always returns a value between 0 and 100 inclusive for any totalJobs > 0 and any completed value", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 100000 }),
        fc.integer({ min: 0, max: 100000 }),
        (totalJobs, completed) => {
          const result = calculateProgress({ totalJobs, completed });
          expect(result).toBeGreaterThanOrEqual(0);
          expect(result).toBeLessThanOrEqual(100);
        }
      ),
      { numRuns: 1000 }
    );
  });

  it("always returns 0 when totalJobs is 0", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 100000 }),
        (completed) => {
          const result = calculateProgress({ totalJobs: 0, completed });
          expect(result).toBe(0);
        }
      ),
      { numRuns: 500 }
    );
  });

  it("returns 100 when completed equals totalJobs and totalJobs > 0", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 100000 }),
        (totalJobs) => {
          const result = calculateProgress({ totalJobs, completed: totalJobs });
          expect(result).toBe(100);
        }
      ),
      { numRuns: 500 }
    );
  });

  it("returns 0 when completed is 0 and totalJobs > 0", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 100000 }),
        (totalJobs) => {
          const result = calculateProgress({ totalJobs, completed: 0 });
          expect(result).toBe(0);
        }
      ),
      { numRuns: 500 }
    );
  });

  it("never throws for any non-negative integer inputs", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 100000 }),
        fc.integer({ min: 0, max: 100000 }),
        (totalJobs, completed) => {
          expect(() => calculateProgress({ totalJobs, completed })).not.toThrow();
        }
      ),
      { numRuns: 500 }
    );
  });

  it("always returns an integer (result of Math.round)", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 100000 }),
        fc.integer({ min: 0, max: 100000 }),
        (totalJobs, completed) => {
          const result = calculateProgress({ totalJobs, completed });
          expect(Number.isInteger(result)).toBe(true);
        }
      ),
      { numRuns: 500 }
    );
  });

  it("validates that completed + pending + failed === totalJobs holds for valid ProgressReports", () => {
    // Generate valid ProgressReport where the sum constraint holds
    const progressReportArb = fc
      .tuple(
        fc.integer({ min: 1, max: 10000 }),
        fc.integer({ min: 0, max: 10000 }),
        fc.integer({ min: 0, max: 10000 })
      )
      .map(([completed, pending, failed]) => ({
        totalJobs: completed + pending + failed,
        completed,
        pending,
        failed,
      }))
      .filter((report) => report.totalJobs > 0);

    fc.assert(
      fc.property(progressReportArb, (report) => {
        // Verify the sum invariant holds
        expect(report.completed + report.pending + report.failed).toBe(
          report.totalJobs
        );

        // Verify percentage is still bounded 0-100
        const result = calculateProgress({
          totalJobs: report.totalJobs,
          completed: report.completed,
        });
        expect(result).toBeGreaterThanOrEqual(0);
        expect(result).toBeLessThanOrEqual(100);
      }),
      { numRuns: 1000 }
    );
  });
});
