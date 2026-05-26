import { describe, it, expect } from "vitest";
import * as fc from "fast-check";
import { validateSearchQuery, ValidationResult } from "./validation";

/**
 * Property-based tests for validateSearchQuery.
 *
 * **Validates: Requirements 7.2, 7.3, 7.4**
 *
 * Property 2: Search Query Validation Completeness
 * For any string s, validateSearchQuery(s) SHALL return { valid: true }
 * if and only if 3 <= s.length <= 300. For all other strings, it SHALL
 * return { valid: false } with the appropriate reason.
 */
describe("validateSearchQuery - Property Tests", () => {
  it("returns { valid: false, reason: 'too_short' } for any string with length < 3", () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 0, maxLength: 2 }),
        (query) => {
          const result = validateSearchQuery(query);
          expect(result).toEqual({ valid: false, reason: "too_short" });
        }
      ),
      { numRuns: 500 }
    );
  });

  it("returns { valid: false, reason: 'too_long' } for any string with length > 300", () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 301, maxLength: 1000 }),
        (query) => {
          const result = validateSearchQuery(query);
          expect(result).toEqual({ valid: false, reason: "too_long" });
        }
      ),
      { numRuns: 500 }
    );
  });

  it("returns { valid: true } for any string with 3 <= length <= 300", () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 3, maxLength: 300 }),
        (query) => {
          const result = validateSearchQuery(query);
          expect(result).toEqual({ valid: true });
        }
      ),
      { numRuns: 500 }
    );
  });

  it("never throws for any string input", () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 0, maxLength: 1000 }),
        (query) => {
          expect(() => validateSearchQuery(query)).not.toThrow();
        }
      ),
      { numRuns: 500 }
    );
  });

  it("always returns one of the three valid result shapes", () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 0, maxLength: 1000 }),
        (query) => {
          const result: ValidationResult = validateSearchQuery(query);

          const isValidShape =
            (result.valid === true) ||
            (result.valid === false && result.reason === "too_short") ||
            (result.valid === false && result.reason === "too_long");

          expect(isValidShape).toBe(true);
        }
      ),
      { numRuns: 500 }
    );
  });
});
