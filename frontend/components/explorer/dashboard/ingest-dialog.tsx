"use client";

import * as React from "react";
import { useState } from "react";
import { Github, Upload, Trash2, AlertCircle, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiClient } from "@/lib/api/client";
import type { Repository } from "@/lib/types/api";

export interface IngestDialogProps {
  existingRepoCount: number;
  existingRepos?: Repository[];
  onIngest: (repoId: number) => void;
  onDelete?: (repoId: number) => void;
  trigger?: React.ReactNode;
}

type IngestMode = "github" | "zip";

const MAX_REPOS = 3;

const GITHUB_URL_PATTERN =
  /^https?:\/\/(www\.)?github\.com\/[\w.-]+\/[\w.-]+\/?$/;

/**
 * Dialog for ingesting a new repository via GitHub URL or ZIP upload.
 * Enforces the maximum repository limit (3).
 * When the limit is reached, shows existing repos with delete options.
 */
export function IngestDialog({
  existingRepoCount,
  existingRepos = [],
  onIngest,
  onDelete,
  trigger,
}: IngestDialogProps) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<IngestMode>("github");
  const [githubUrl, setGithubUrl] = useState("");
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRetryable, setIsRetryable] = useState(false);

  const isLimitReached = existingRepoCount >= MAX_REPOS;

  const isGithubUrlValid = GITHUB_URL_PATTERN.test(githubUrl.trim());
  const canSubmit =
    !isSubmitting &&
    ((mode === "github" && isGithubUrlValid) ||
      (mode === "zip" && zipFile !== null));

  function resetForm() {
    setGithubUrl("");
    setZipFile(null);
    setError(null);
    setIsRetryable(false);
    setMode("github");
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    setError(null);
    setIsRetryable(false);

    try {
      let response: { repository_id: number };

      if (mode === "github") {
        response = await apiClient.post<{ repository_id: number }>(
          "/api/repositories/",
          { github_url: githubUrl.trim() }
        );
      } else {
        // For ZIP upload, use FormData
        const formData = new FormData();
        formData.append("zip_file", zipFile!);

        response = await apiClient.postForm<{ repository_id: number }>(
          "/api/repositories/",
          formData
        );
      }

      // Success (202 Accepted)
      onIngest(response.repository_id);
      resetForm();
      setOpen(false);
    } catch (err: unknown) {
      // Network error or API error
      const isNetworkOrServer =
        err instanceof TypeError ||
        (err !== null &&
          typeof err === "object" &&
          "status" in err &&
          typeof (err as { status: number }).status === "number" &&
          (err as { status: number }).status >= 500);

      const message =
        err !== null &&
        typeof err === "object" &&
        "message" in err &&
        typeof (err as { message: string }).message === "string"
          ? (err as { message: string }).message
          : "Something went wrong";

      setError(message);
      setIsRetryable(isNetworkOrServer);
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setZipFile(file);
    setError(null);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        setOpen(value);
        if (!value) resetForm();
      }}
    >
      <DialogTrigger asChild>
        {trigger || (
          <Button>
            <Upload className="mr-2 h-4 w-4" />
            Ingest Repository
          </Button>
        )}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Ingest Repository</DialogTitle>
          <DialogDescription>
            {isLimitReached
              ? "You've reached the maximum of 3 repositories. Delete one to add a new repository."
              : "Add a new repository from GitHub or upload a ZIP file."}
          </DialogDescription>
        </DialogHeader>

        {isLimitReached ? (
          <LimitReachedContent
            repos={existingRepos}
            onDelete={onDelete}
          />
        ) : (
          <IngestForm
            mode={mode}
            onModeChange={setMode}
            githubUrl={githubUrl}
            onGithubUrlChange={setGithubUrl}
            isGithubUrlValid={isGithubUrlValid}
            zipFile={zipFile}
            onFileChange={handleFileChange}
            canSubmit={canSubmit}
            isSubmitting={isSubmitting}
            error={error}
            isRetryable={isRetryable}
            onSubmit={handleSubmit}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}


// --- Sub-components ---

interface LimitReachedContentProps {
  repos: Repository[];
  onDelete?: (repoId: number) => void;
}

function LimitReachedContent({ repos, onDelete }: LimitReachedContentProps) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Your existing repositories:
      </p>
      <ul className="space-y-2">
        {repos.map((repo) => (
          <li
            key={repo.id}
            className="flex items-center justify-between rounded-md border p-3"
          >
            <div className="flex items-center gap-2">
              {repo.sourceType === "github" ? (
                <Github className="h-4 w-4 text-muted-foreground" />
              ) : (
                <Upload className="h-4 w-4 text-muted-foreground" />
              )}
              <span className="text-sm font-medium">{repo.name}</span>
            </div>
            {onDelete && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDelete(repo.id)}
                aria-label={`Delete ${repo.name}`}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

interface IngestFormProps {
  mode: IngestMode;
  onModeChange: (mode: IngestMode) => void;
  githubUrl: string;
  onGithubUrlChange: (url: string) => void;
  isGithubUrlValid: boolean;
  zipFile: File | null;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  canSubmit: boolean;
  isSubmitting: boolean;
  error: string | null;
  isRetryable: boolean;
  onSubmit: () => void;
}

function IngestForm({
  mode,
  onModeChange,
  githubUrl,
  onGithubUrlChange,
  isGithubUrlValid,
  zipFile,
  onFileChange,
  canSubmit,
  isSubmitting,
  error,
  isRetryable,
  onSubmit,
}: IngestFormProps) {
  return (
    <div className="space-y-4">
      {/* Mode toggle */}
      <div className="flex gap-2">
        <Button
          variant={mode === "github" ? "default" : "outline"}
          size="sm"
          onClick={() => onModeChange("github")}
          type="button"
        >
          <Github className="mr-2 h-4 w-4" />
          GitHub URL
        </Button>
        <Button
          variant={mode === "zip" ? "default" : "outline"}
          size="sm"
          onClick={() => onModeChange("zip")}
          type="button"
        >
          <Upload className="mr-2 h-4 w-4" />
          ZIP Upload
        </Button>
      </div>

      {/* Form fields */}
      {mode === "github" ? (
        <div className="space-y-2">
          <Label htmlFor="github-url">GitHub Repository URL</Label>
          <Input
            id="github-url"
            type="url"
            placeholder="https://github.com/owner/repo"
            value={githubUrl}
            onChange={(e) => onGithubUrlChange(e.target.value)}
            aria-invalid={githubUrl.length > 0 && !isGithubUrlValid}
            aria-describedby="github-url-hint"
          />
          {githubUrl.length > 0 && !isGithubUrlValid && (
            <p id="github-url-hint" className="text-xs text-destructive">
              Please enter a valid GitHub repository URL (e.g.,
              https://github.com/owner/repo)
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <Label htmlFor="zip-file">ZIP File</Label>
          <Input
            id="zip-file"
            type="file"
            accept=".zip"
            onChange={onFileChange}
            aria-describedby="zip-file-hint"
          />
          {zipFile && (
            <p id="zip-file-hint" className="text-xs text-muted-foreground">
              Selected: {zipFile.name}
            </p>
          )}
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/50 bg-destructive/10 p-3">
          <AlertCircle className="mt-0.5 h-4 w-4 text-destructive" />
          <div className="space-y-1">
            <p className="text-sm text-destructive">{error}</p>
            {isRetryable && (
              <p className="text-xs text-muted-foreground">
                This may be a temporary issue. You can try again.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Submit button */}
      <Button
        className="w-full"
        onClick={onSubmit}
        disabled={!canSubmit}
        type="button"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Ingesting...
          </>
        ) : (
          <>
            {isRetryable ? "Retry" : "Start Ingestion"}
          </>
        )}
      </Button>
    </div>
  );
}
