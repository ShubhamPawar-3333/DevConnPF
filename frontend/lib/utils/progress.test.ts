import { describe, it, expect } from "vitest";
import { calculateProgress } from "./progress";

describe("calculateProgress", () => {
  it("returns 0 when totalJobs is 0", () => {
    expect(calculateProgress({ totalJobs: 0, completed: 0 })).toBe(0);
  });

  it("returns 0 when no jobs are completed", () => {
    expect(calculateProgress({ totalJobs: 10, completed: 0 })).toBe(0);
  });

  it("returns 100 when all jobs are completed", () => {
    expect(calculateProgress({ totalJobs: 10, completed: 10 })).toBe(100);
  });

  it("returns 50 when half the jobs are completed", () => {
    expect(calculateProgress({ totalJobs: 10, completed: 5 })).toBe(50);
  });

  it("rounds to nearest integer", () => {
    // 1/3 = 33.33... → 33
    expect(calculateProgress({ totalJobs: 3, completed: 1 })).toBe(33);
    // 2/3 = 66.66... → 67
    expect(calculateProgress({ totalJobs: 3, completed: 2 })).toBe(67);
  });

  it("clamps to 100 when completed exceeds totalJobs", () => {
    expect(calculateProgress({ totalJobs: 5, completed: 10 })).toBe(100);
  });

  it("clamps to 0 when completed is negative", () => {
    expect(calculateProgress({ totalJobs: 10, completed: -5 })).toBe(0);
  });

  it("handles single job completed", () => {
    expect(calculateProgress({ totalJobs: 1, completed: 1 })).toBe(100);
  });

  it("handles large numbers", () => {
    expect(calculateProgress({ totalJobs: 10000, completed: 5000 })).toBe(50);
  });
});
