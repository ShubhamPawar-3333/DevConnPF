"use client";

import { AlertCircle, Globe, Loader2 } from "lucide-react";
import type { LanguageCode, SummaryStatus } from "@/lib/types/api";

/**
 * Map of language codes to human-readable display names.
 */
const LANGUAGE_NAMES: Record<LanguageCode, string> = {
  en: "English",
  es: "Spanish",
  fr: "French",
  de: "German",
  pt: "Portuguese",
  ja: "Japanese",
  ko: "Korean",
  zh: "Chinese",
};

interface SummaryDisplayProps {
  /** The summary text to display */
  text: string | null;
  /** The summary's current status */
  status: SummaryStatus;
  /** The language the summary is actually in */
  summaryLanguage?: LanguageCode;
  /** The user's preferred language */
  preferredLanguage?: LanguageCode;
}

/**
 * Displays an AI-generated summary with language awareness.
 *
 * - If the summary language matches the user's preference: displays normally.
 * - If the summary language doesn't match (e.g., summary is in English but user
 *   prefers Japanese): shows the summary with a notice indicating the preferred
 *   language is unavailable.
 * - Handles pending/failed/not_applicable states with appropriate messages.
 */
export function SummaryDisplay({
  text,
  status,
  summaryLanguage,
  preferredLanguage,
}: SummaryDisplayProps) {
  switch (status) {
    case "completed":
      return (
        <div className="space-y-2">
          <LanguageMismatchNotice
            summaryLanguage={summaryLanguage}
            preferredLanguage={preferredLanguage}
          />
          <p className="text-sm leading-relaxed text-foreground">{text}</p>
        </div>
      );
    case "pending":
      return (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Summary is being generated...</span>
        </div>
      );
    case "failed":
    case "permanently_failed":
      return (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <AlertCircle className="h-4 w-4" />
          <span>Summary could not be generated.</span>
        </div>
      );
    default:
      return (
        <p className="text-sm text-muted-foreground">No summary available.</p>
      );
  }
}

/**
 * Shows a notice when the summary language doesn't match the user's preference.
 * Only renders when both languages are provided and they differ.
 */
function LanguageMismatchNotice({
  summaryLanguage,
  preferredLanguage,
}: {
  summaryLanguage?: LanguageCode;
  preferredLanguage?: LanguageCode;
}) {
  // Don't show notice if languages aren't provided or they match
  if (!summaryLanguage || !preferredLanguage) return null;
  if (summaryLanguage === preferredLanguage) return null;

  const displayLanguage = LANGUAGE_NAMES[summaryLanguage] ?? summaryLanguage;

  return (
    <div className="flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
      <Globe className="h-3.5 w-3.5 shrink-0" />
      <span>
        Shown in {displayLanguage} — preferred language not available
      </span>
    </div>
  );
}
