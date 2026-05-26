import { describe, it, expect } from "vitest";
import * as fc from "fast-check";
import { truncateSearchExcerpt } from "@/lib/utils/truncate";
import type { SearchResult } from "@/lib/types/api";

/**
 * Property 7: Search Excerpt Length Bound
 *
 * For any SearchResult with summaryExcerpt of any length,
 * the displayed excerpt is always ≤ 200 characters.
 * If summaryExcerpt ≤ 200 chars, it's displayed unchanged.
 * If summaryExcerpt > 200 chars, the displayed version is exactly 200 chars and ends with "...".
 * The truncation function never throws for any string input.
 *
 * **Validates: Requirements 7.5**
 */
describe("Property 7: Search Excerpt Length Bound", () => {
  // Arbitrary for generating SearchResult objects
  const searchResultArb: fc.Arbitrary<SearchResult> = fc.record({
    filePath: fc.string({ minLength: 1 }),
    blockName: fc.option(fc.string(), { nil: null }),
    summaryExcerpt: fc.string({ minLength: 0, maxLength: 1000 }),
    similarityRank: fc.float({ min: 0, max: 1, noNaN: true }),
    resultType: fc.constantFrom("file" as const, "block" as const),
    fileId: fc.integer({ min: 1 }),
    blockId: fc.option(fc.integer({ min: 1 }), { nil: null }),
  });

  it("truncated excerpt is always ≤ 200 characters for any input", () => {
    fc.assert(
      fc.property(searchResultArb, (result) => {
        const truncated = truncateSearchExcerpt(result.summaryExcerpt);
        expect(truncated.length).toBeLessThanOrEqual(200);
      }),
      { numRuns: 500 }
    );
  });

  it("excerpts ≤ 200 characters are displayed unchanged", () => {
    const shortExcerptArb = fc.string({ minLength: 0, maxLength: 200 });

    fc.assert(
      fc.property(shortExcerptArb, (excerpt) => {
        const truncated = truncateSearchExcerpt(excerpt);
        expect(truncated).toBe(excerpt);
      }),
      { numRuns: 500 }
    );
  });

  it("excerpts > 200 characters are exactly 200 chars and end with '...'", () => {
    const longExcerptArb = fc.string({ minLength: 201, maxLength: 1000 });

    fc.assert(
      fc.property(longExcerptArb, (excerpt) => {
        const truncated = truncateSearchExcerpt(excerpt);
        expect(truncated.length).toBe(200);
        expect(truncated.endsWith("...")).toBe(true);
      }),
      { numRuns: 500 }
    );
  });

  it("never throws for any string input", () => {
    fc.assert(
      fc.property(fc.string(), (excerpt) => {
        // Should never throw
        expect(() => truncateSearchExcerpt(excerpt)).not.toThrow();
      }),
      { numRuns: 500 }
    );
  });
});
