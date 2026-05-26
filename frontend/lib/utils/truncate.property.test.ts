import { describe, it, expect } from "vitest";
import * as fc from "fast-check";
import { truncateSummary } from "./truncate";

/**
 * Property 6: Summary Preview Truncation
 *
 * For any string input to the truncation function, the output length SHALL be
 * at most 80 characters. If the input exceeds 80 characters, the output SHALL
 * end with "…" (ellipsis) and have a total length of exactly 80 characters.
 *
 * **Validates: Requirements 5.4**
 */
describe("Property 6: Summary Preview Truncation", () => {
  it("output is always ≤ 80 characters for any input string", () => {
    fc.assert(
      fc.property(fc.string({ minLength: 0, maxLength: 5000 }), (input) => {
        const result = truncateSummary(input);
        expect(result.length).toBeLessThanOrEqual(80);
      })
    );
  });

  it("if input length > 80, output is exactly 80 characters", () => {
    fc.assert(
      fc.property(fc.string({ minLength: 81, maxLength: 5000 }), (input) => {
        const result = truncateSummary(input);
        expect(result.length).toBe(80);
      })
    );
  });

  it("if input length > 80, output ends with '…' (U+2026)", () => {
    fc.assert(
      fc.property(fc.string({ minLength: 81, maxLength: 5000 }), (input) => {
        const result = truncateSummary(input);
        expect(result.endsWith("\u2026")).toBe(true);
      })
    );
  });

  it("if input length ≤ 80, output equals input unchanged", () => {
    fc.assert(
      fc.property(fc.string({ minLength: 0, maxLength: 80 }), (input) => {
        const result = truncateSummary(input);
        expect(result).toBe(input);
      })
    );
  });

  it("for null/undefined input, output is empty string", () => {
    expect(truncateSummary(null)).toBe("");
    expect(truncateSummary(undefined)).toBe("");
  });

  it("the function never throws for any input", () => {
    fc.assert(
      fc.property(
        fc.oneof(
          fc.string({ minLength: 0, maxLength: 5000 }),
          fc.constant(null as string | null | undefined),
          fc.constant(undefined as string | null | undefined)
        ),
        (input) => {
          expect(() => truncateSummary(input)).not.toThrow();
        }
      )
    );
  });
});
