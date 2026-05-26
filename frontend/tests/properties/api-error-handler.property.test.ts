import { describe, it, expect } from "vitest";
import * as fc from "fast-check";
import { handleApiError, type ErrorAction } from "@/lib/api/error-handler";
import type { ApiError } from "@/lib/types/api";

/**
 * Property 4: API Error Handler Totality
 *
 * For any ApiError with a numeric status field (100-599),
 * handleApiError always returns a valid ErrorAction without throwing.
 * Specific status codes map to deterministic actions.
 *
 * **Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5**
 */
describe("Property 4: API Error Handler Totality", () => {
  // Arbitrary for generating ApiError objects with status codes 100-599
  const apiErrorArb: fc.Arbitrary<ApiError> = fc.record({
    status: fc.integer({ min: 100, max: 599 }),
    message: fc.string(),
    detail: fc.option(fc.string(), { nil: undefined }),
    code: fc.option(fc.string(), { nil: undefined }),
  });

  it("never throws for any valid HTTP status code", () => {
    fc.assert(
      fc.property(apiErrorArb, (error) => {
        // Should never throw
        const result = handleApiError(error);
        expect(result).toBeDefined();
      }),
      { numRuns: 500 }
    );
  });

  it("always returns a valid ErrorAction (one of redirect, toast, or not-found)", () => {
    fc.assert(
      fc.property(apiErrorArb, (error) => {
        const result = handleApiError(error);

        // Must be one of the three valid action types
        const validTypes = ["redirect", "toast", "not-found"];
        expect(validTypes).toContain(result.type);

        // Type-specific field validation
        if (result.type === "redirect") {
          expect(result).toHaveProperty("target");
          expect(typeof result.target).toBe("string");
          expect(result.target.length).toBeGreaterThan(0);
        } else if (result.type === "toast") {
          expect(result).toHaveProperty("message");
          expect(typeof result.message).toBe("string");
          expect(result.message.length).toBeGreaterThan(0);
        }
        // "not-found" has no additional fields to validate
      }),
      { numRuns: 500 }
    );
  });

  it("401 always returns redirect to /login", () => {
    fc.assert(
      fc.property(fc.string(), fc.option(fc.string(), { nil: undefined }), (message, detail) => {
        const error: ApiError = { status: 401, message, detail };
        const result = handleApiError(error);

        expect(result).toEqual({ type: "redirect", target: "/login" });
      }),
      { numRuns: 100 }
    );
  });

  it("403 always returns permission denied toast", () => {
    fc.assert(
      fc.property(fc.string(), fc.option(fc.string(), { nil: undefined }), (message, detail) => {
        const error: ApiError = { status: 403, message, detail };
        const result = handleApiError(error);

        expect(result).toEqual({
          type: "toast",
          message: "You don't have permission for this action",
        });
      }),
      { numRuns: 100 }
    );
  });

  it("404 always returns not-found action", () => {
    fc.assert(
      fc.property(fc.string(), fc.option(fc.string(), { nil: undefined }), (message, detail) => {
        const error: ApiError = { status: 404, message, detail };
        const result = handleApiError(error);

        expect(result).toEqual({ type: "not-found" });
      }),
      { numRuns: 100 }
    );
  });

  it("429 always returns rate-limit toast", () => {
    fc.assert(
      fc.property(fc.string(), fc.option(fc.string(), { nil: undefined }), (message, detail) => {
        const error: ApiError = { status: 429, message, detail };
        const result = handleApiError(error);

        expect(result).toEqual({
          type: "toast",
          message: "Too many requests. Please wait a moment.",
        });
      }),
      { numRuns: 100 }
    );
  });

  it("all other status codes return a toast with a non-empty message", () => {
    // Generate status codes that are NOT 401, 403, 404, or 429
    const otherStatusArb = fc.integer({ min: 100, max: 599 }).filter(
      (s) => s !== 401 && s !== 403 && s !== 404 && s !== 429
    );

    fc.assert(
      fc.property(otherStatusArb, fc.string(), (status, message) => {
        const error: ApiError = { status, message };
        const result = handleApiError(error);

        expect(result.type).toBe("toast");
        if (result.type === "toast") {
          expect(result.message.length).toBeGreaterThan(0);
          // If the error message is non-empty, it should be used directly
          if (message.length > 0) {
            expect(result.message).toBe(message);
          } else {
            // Empty message falls back to "Something went wrong"
            expect(result.message).toBe("Something went wrong");
          }
        }
      }),
      { numRuns: 300 }
    );
  });
});
