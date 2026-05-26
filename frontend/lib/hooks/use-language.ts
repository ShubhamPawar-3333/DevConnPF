"use client";

import { useAuth } from "@/lib/auth/auth-context";
import type { LanguageCode } from "@/lib/types/api";

/**
 * Returns the current user's language preference.
 * Falls back to "en" if the user is not authenticated or preference is unavailable.
 */
export function useLanguage(): LanguageCode {
  const { user } = useAuth();
  return user?.languagePreference ?? "en";
}
