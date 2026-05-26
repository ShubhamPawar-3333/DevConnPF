/**
 * Truncates a summary string to a maximum of 80 characters.
 *
 * - If input is null or undefined, returns an empty string
 * - If input length is ≤ 80, returns it unchanged
 * - If input length is > 80, truncates to 79 chars and appends "…" (U+2026),
 *   resulting in exactly 80 characters
 *
 * @param input - The summary string to truncate
 * @returns A string of at most 80 characters
 */
export function truncateSummary(input: string | null | undefined): string {
  if (input == null) {
    return "";
  }

  if (input.length <= 80) {
    return input;
  }

  return input.slice(0, 79) + "\u2026";
}

/**
 * Truncates a search result excerpt to a maximum of 200 characters.
 *
 * - If input length is ≤ 200, returns it unchanged
 * - If input length is > 200, truncates to 197 chars and appends "...",
 *   resulting in exactly 200 characters
 *
 * @param excerpt - The summary excerpt string to truncate
 * @returns A string of at most 200 characters
 */
export function truncateSearchExcerpt(excerpt: string): string {
  if (excerpt.length <= 200) {
    return excerpt;
  }

  return excerpt.slice(0, 197) + "...";
}
