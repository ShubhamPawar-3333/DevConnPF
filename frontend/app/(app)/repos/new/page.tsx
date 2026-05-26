"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Github, Upload, Trash2, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ProgressPanel } from "@/components/explorer/progress/progress-panel";
import { apiClient } from "@/lib/api/client";
import type { Repository } from "@/lib/types/api";

type IngestMode = "github" | "zip";

const MAX_REPOS = 3;

const GITHUB_URL_PATTERN =
  /^https?:\/\/(www\.)?github\.com\/[\w.-]+\/[\w.-]+\/?$/;

/**
 * Repository ingestion page.
 *
 * Flow:
 * 1. Fetches existing repos to determine count and enforce limit (max 3)
 * 2. Shows inline ingestion form (GitHub URL or ZIP upload)
 * 3. On successful ingestion (202 response with repository_id), shows ProgressPanel
 * 4. ProgressPanel polls every 5s until terminal status
 * 5. On complete, navigates to /repos/[id]/tree
 *
 * Requirements: 4.1, 4.2, 4.3, 4.4
 */
export default function NewRepoPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  // State for ingestion flow
  const [repositoryId, setRepositoryId] = useState<number | null>(null);
  const [mode, setMode] = useState<IngestMode>("github");
  const [githubUrl, setGithubUrl] = useState("");
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRetryable, setIsRetryable] = useState(false);

  // Fetch existing repositories to check count and enforce limit
  const { data: existingRepos = [], isLoading: isLoadingRepos } = useQuery<Repository[]>({
    queryKey: ["repositories"],
    queryFn: () => apiClient.get<Repository[]>("/api/repositories/"),
  });

  const existingRepoCount = existingRepos.length;
  const isLimitReached = existingRepoCount >= MAX_REPOS;

  // Validation
  const isGithubUrlValid = GITHUB_URL_PATTERN.test(githubUrl.trim());
  const canSubmit =
    !isLimitReached &&
    ((mode === "github" && isGithubUrlValid) ||
      (mode === "zip" && zipFile !== null));

  // Ingestion mutation
  const ingestMutation = useMutation({
    mutationFn: async (): Promise<{ repository_id: number }> => {
      if (mode === "github") {
        return apiClient.post<{ repository_id: number }>(
          "/api/repositories/",
          { github_url: githubUrl.trim() }
        );
      } else {
        // ZIP upload uses FormData
        const formData = new FormData();
        formData.append("zip_file", zipFile!);

        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/repositories/`,
          {
            method: "POST",
            credentials: "include",
            body: formData,
          }
        );

        if (!res.ok) {
          const body = await res.json().catch(() => null);
          const message = body?.message || body?.detail || "Upload failed";
          const isServerOrNetwork = res.status >= 500;
          const err = new Error(message) as Error & { isRetryable: boolean };
          err.isRetryable = isServerOrNetwork;
          throw err;
        }

        return res.json();
      }
    },
    onSuccess: (data) => {
      setRepositoryId(data.repository_id);
      setError(null);
      setIsRetryable(false);
      // Invalidate repos list cache
      queryClient.invalidateQueries({ queryKey: ["repositories"] });
    },
    onError: (err: unknown) => {
      const isNetworkOrServer =
        err instanceof TypeError ||
        (err !== null &&
          typeof err === "object" &&
          "isRetryable" in err &&
          (err as { isRetryable: boolean }).isRetryable) ||
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
    },
  });

  // Delete repository mutation (for limit enforcement)
  const deleteMutation = useMutation({
    mutationFn: (repoId: number) =>
      apiClient.delete(`/api/repositories/${repoId}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["repositories"] });
    },
  });

  // Handle ingestion completion — navigate to tree view
  const handleComplete = useCallback(() => {
    if (repositoryId) {
      router.push(`/repos/${repositoryId}/tree`);
    }
  }, [repositoryId, router]);

  function handleSubmit() {
    setError(null);
    setIsRetryable(false);
    ingestMutation.mutate();
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setZipFile(file);
    setError(null);
  }

  // If ingestion has started, show progress tracker
  if (repositoryId) {
    return (
      <div className="mx-auto max-w-lg space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Ingesting Repository</CardTitle>
            <CardDescription>
              Your repository is being processed. This may take a few minutes.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ProgressPanel repoId={repositoryId} onComplete={handleComplete} />
          </CardContent>
        </Card>
      </div>
    );
  }

  // Loading state while fetching existing repos
  if (isLoadingRepos) {
    return (
      <div className="mx-auto max-w-lg space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Ingest Repository</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="h-10 animate-pulse rounded bg-muted" />
              <div className="h-10 animate-pulse rounded bg-muted" />
              <div className="h-10 animate-pulse rounded bg-muted" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Ingest Repository</CardTitle>
          <CardDescription>
            {isLimitReached
              ? "You've reached the maximum of 3 repositories. Delete one to add a new repository."
              : "Add a new repository from GitHub or upload a ZIP file."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLimitReached ? (
            <LimitReachedContent
              repos={existingRepos}
              onDelete={(repoId) => deleteMutation.mutate(repoId)}
            />
          ) : (
            <div className="space-y-4">
              {/* Mode toggle */}
              <div className="flex gap-2">
                <Button
                  variant={mode === "github" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setMode("github")}
                  type="button"
                >
                  <Github className="mr-2 h-4 w-4" />
                  GitHub URL
                </Button>
                <Button
                  variant={mode === "zip" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setMode("zip")}
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
                    onChange={(e) => setGithubUrl(e.target.value)}
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
                    onChange={handleFileChange}
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
                onClick={handleSubmit}
                disabled={!canSubmit || ingestMutation.isPending}
                type="button"
              >
                {ingestMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Ingesting...
                  </>
                ) : (
                  <>{isRetryable ? "Retry" : "Start Ingestion"}</>
                )}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// --- Sub-component ---

interface LimitReachedContentProps {
  repos: Repository[];
  onDelete: (repoId: number) => void;
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
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(repo.id)}
              aria-label={`Delete ${repo.name}`}
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
