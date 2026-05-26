"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth/auth-context";
import { useUpdateLanguage } from "@/lib/hooks/use-language-preference";
import type { LanguageCode } from "@/lib/types/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

const LANGUAGE_OPTIONS: { value: LanguageCode; label: string }[] = [
  { value: "en", label: "English" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "pt", label: "Portuguese" },
  { value: "ja", label: "Japanese" },
  { value: "ko", label: "Korean" },
  { value: "zh", label: "Chinese" },
];

export default function SettingsPage() {
  const { user } = useAuth();
  const updateLanguage = useUpdateLanguage();

  const [selectedLanguage, setSelectedLanguage] = useState<LanguageCode>(
    user?.languagePreference ?? "en"
  );
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Sync selected language when user data loads or changes
  useEffect(() => {
    if (user?.languagePreference) {
      setSelectedLanguage(user.languagePreference);
    }
  }, [user?.languagePreference]);

  const handleSave = () => {
    setSuccessMessage(null);
    setErrorMessage(null);

    updateLanguage.mutate(selectedLanguage, {
      onSuccess: () => {
        setSuccessMessage("Language preference saved");
      },
      onError: () => {
        // Retain previous selection on error
        setSelectedLanguage(user?.languagePreference ?? "en");
        setErrorMessage("Failed to save preference");
      },
    });
  };

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Language Preference</CardTitle>
          <CardDescription>
            Choose the language for AI-generated summaries.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="language-select">Preferred Language</Label>
            <select
              id="language-select"
              value={selectedLanguage}
              onChange={(e) => {
                setSelectedLanguage(e.target.value as LanguageCode);
                setSuccessMessage(null);
                setErrorMessage(null);
              }}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={updateLanguage.isPending}
            >
              {LANGUAGE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <Button
            onClick={handleSave}
            disabled={updateLanguage.isPending}
          >
            {updateLanguage.isPending ? "Saving..." : "Save"}
          </Button>

          {successMessage && (
            <p className="text-sm text-green-600" role="status">
              {successMessage}
            </p>
          )}

          {errorMessage && (
            <p className="text-sm text-destructive" role="alert">
              {errorMessage}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
