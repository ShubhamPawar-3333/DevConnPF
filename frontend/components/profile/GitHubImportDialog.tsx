"use client";

import { useState } from "react";
import { Github, RefreshCw } from "lucide-react";
import { useGitHubImportPreview, useApplyGitHubImport } from "@/lib/hooks/use-profiles";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface GitHubImportDialogProps {
  open: boolean;
  onClose: () => void;
  onImported: () => void;
}

/**
 * Modal showing current profile values vs fetched GitHub values.
 * User selects which fields to overwrite, then confirms.
 */
export function GitHubImportDialog({ open, onClose, onImported }: GitHubImportDialogProps) {
  const {
    data: preview,
    isLoading: previewLoading,
    isError: previewError,
    error: previewErr,
    refetch: fetchPreview,
  } = useGitHubImportPreview();

  const { mutate: applyImport, isPending: applying } = useApplyGitHubImport();

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [applyError, setApplyError] = useState("");

  // Fetch preview when dialog opens
  function handleOpen() {
    if (!preview) fetchPreview();
    setSelected(new Set());
    setApplyError("");
  }

  function toggleField(field: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(field) ? next.delete(field) : next.add(field);
      return next;
    });
  }

  function handleApply() {
    setApplyError("");
    applyImport(Array.from(selected), {
      onSuccess: () => {
        onImported();
        onClose();
      },
      onError: (err: unknown) => {
        const apiErr = err as { message?: string };
        setApplyError(apiErr?.message ?? "Failed to import. Please try again.");
      },
    });
  }

  // Re-fetch on open
  function handleOpenChange(open: boolean) {
    if (open) handleOpen();
    else onClose();
  }

  const githubData = preview?.github_data ?? {};
  const currentProfile = preview?.current_profile;

  // Importable fields with labels
  const importableFields: { key: string; label: string }[] = [
    { key: "display_name", label: "Display name" },
    { key: "avatar_url", label: "Avatar" },
    { key: "bio", label: "Bio" },
  ];

  // Only show fields returned by GitHub
  const availableFields = importableFields.filter(
    (f) => githubData[f.key as keyof typeof githubData]
  );

  const isTokenError =
    previewError &&
    typeof previewErr === "object" &&
    previewErr !== null &&
    "action" in previewErr;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Github className="h-5 w-5" />
            Import from GitHub
          </DialogTitle>
        </DialogHeader>

        {previewLoading && (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">Fetching GitHub data…</span>
          </div>
        )}

        {previewError && (
          <div className="space-y-3 py-4">
            <p className="text-sm text-destructive">
              {isTokenError
                ? "Your GitHub authorization is invalid. Please re-authenticate."
                : "Failed to fetch GitHub profile data."}
            </p>
            {isTokenError && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => { window.location.href = "/api/auth/github/"; }}
              >
                Re-authenticate with GitHub
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={() => fetchPreview()}>
              Try again
            </Button>
          </div>
        )}

        {preview && !previewLoading && (
          <div className="space-y-4">
            {availableFields.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No importable data found on your GitHub profile.
              </p>
            ) : (
              <>
                <p className="text-sm text-muted-foreground">
                  Select the fields you want to overwrite with your GitHub data.
                </p>

                <div className="divide-y rounded-md border">
                  {availableFields.map(({ key, label }) => {
                    const ghValue = githubData[key as keyof typeof githubData];
                    const currentValue = currentProfile?.[key as keyof typeof currentProfile];
                    const isChecked = selected.has(key);

                    return (
                      <label
                        key={key}
                        className="flex items-start gap-3 p-3 cursor-pointer hover:bg-muted/50 transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleField(key)}
                          className="mt-1 h-4 w-4 rounded border"
                        />
                        <div className="flex-1 min-w-0 space-y-1">
                          <p className="text-sm font-medium">{label}</p>
                          <p className="text-xs text-muted-foreground truncate">
                            Current: {currentValue ?? <em>not set</em>}
                          </p>
                          <p className="text-xs text-primary truncate">
                            GitHub: {String(ghValue)}
                          </p>
                        </div>
                      </label>
                    );
                  })}
                </div>

                {applyError && (
                  <p className="text-xs text-destructive">{applyError}</p>
                )}

                <div className="flex gap-2">
                  <Button variant="outline" className="flex-1" onClick={onClose}>
                    Cancel
                  </Button>
                  <Button
                    className="flex-1"
                    onClick={handleApply}
                    disabled={selected.size === 0 || applying}
                  >
                    {applying ? "Importing…" : `Import ${selected.size} field${selected.size !== 1 ? "s" : ""}`}
                  </Button>
                </div>
              </>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
