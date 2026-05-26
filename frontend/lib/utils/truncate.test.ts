import { describe, it, expect } from "vitest";
import { truncateSummary } from "./truncate";

describe("truncateSummary", () => {
  it("returns empty string for null input", () => {
    expect(truncateSummary(null)).toBe("");
  });

  it("returns empty string for undefined input", () => {
    expect(truncateSummary(undefined)).toBe("");
  });

  it("returns empty string unchanged", () => {
    expect(truncateSummary("")).toBe("");
  });

  it("returns short strings unchanged", () => {
    expect(truncateSummary("hello")).toBe("hello");
  });

  it("returns a string of exactly 80 chars unchanged", () => {
    const input = "a".repeat(80);
    expect(truncateSummary(input)).toBe(input);
    expect(truncateSummary(input).length).toBe(80);
  });

  it("truncates a string of 81 chars to exactly 80 chars ending with ellipsis", () => {
    const input = "a".repeat(81);
    const result = truncateSummary(input);
    expect(result.length).toBe(80);
    expect(result.endsWith("\u2026")).toBe(true);
    expect(result).toBe("a".repeat(79) + "\u2026");
  });

  it("truncates long strings to exactly 80 chars", () => {
    const input = "b".repeat(200);
    const result = truncateSummary(input);
    expect(result.length).toBe(80);
    expect(result.endsWith("\u2026")).toBe(true);
  });

  it("preserves content before truncation point", () => {
    const input = "Hello World! ".repeat(10); // 130 chars
    const result = truncateSummary(input);
    expect(result.length).toBe(80);
    expect(result.slice(0, 79)).toBe(input.slice(0, 79));
    expect(result[79]).toBe("\u2026");
  });

  it("does not add ellipsis when string is within limit", () => {
    const input = "Short summary text";
    const result = truncateSummary(input);
    expect(result).toBe(input);
    expect(result.includes("\u2026")).toBe(false);
  });
});
