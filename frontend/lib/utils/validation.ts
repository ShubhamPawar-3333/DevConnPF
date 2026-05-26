/**
 * Search query validation utility.
 *
 * Validates search queries against length constraints:
 * - Minimum: 3 characters
 * - Maximum: 300 characters
 *
 * Pure function, no side effects.
 */

export type ValidationResult =
  | { valid: true }
  | { valid: false; reason: "too_short" | "too_long" };

/**
 * Validates a search query string against length constraints.
 *
 * @param query - The search query string to validate
 * @returns ValidationResult indicating whether the query is valid,
 *   or the reason it's invalid ("too_short" or "too_long")
 */
export function validateSearchQuery(query: string): ValidationResult {
  if (query.length < 3) {
    return { valid: false, reason: "too_short" };
  }

  if (query.length > 300) {
    return { valid: false, reason: "too_long" };
  }

  return { valid: true };
}
