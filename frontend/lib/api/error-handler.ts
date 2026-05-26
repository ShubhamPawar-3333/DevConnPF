import type { ApiError } from "@/lib/types/api";

export type ErrorAction =
  | { type: "redirect"; target: string }
  | { type: "toast"; message: string }
  | { type: "not-found" };

/**
 * Maps an API error to a user-facing action.
 * Pure function — no side effects, never throws.
 *
 * - 401 → redirect to login
 * - 403 → permission denied toast
 * - 404 → not-found page
 * - 429 → rate limit toast
 * - All others → generic toast with error message or fallback
 */
export function handleApiError(error: ApiError): ErrorAction {
  switch (error.status) {
    case 401:
      return { type: "redirect", target: "/login" };
    case 403:
      return { type: "toast", message: "You don't have permission for this action" };
    case 404:
      return { type: "not-found" };
    case 429:
      return { type: "toast", message: "Too many requests. Please wait a moment." };
    default:
      return { type: "toast", message: error.message || "Something went wrong" };
  }
}
