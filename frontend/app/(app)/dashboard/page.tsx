"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { AlertCircle, FolderOpen } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { AuthGuard } from "@/lib/auth/auth-guard";
import { RepoCard } from "@/components/explorer/dashboard/repo-card";
import { IngestDialog } from "@/components/explorer/dashboard/ingest-dialog";
import { Button } from "@/components/ui/button";
import type { Repository } from "@/lib/types/api";

function DashboardContent() {
  const router = useRouter();

  const {
    data: repositories,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<Repository[]>({
    queryKey: ["repositories"],
    queryFn: () => apiClient.get<Repository[]>("/api/repositories/"),
  });

  // Sort by ingestion date descending (most recent first)
  const sortedRepos = repositories
    ? [...repositories].sort(
        (a, b) =>
          new Date(b.ingestedAt).getTime() - new Date(a.ingestedAt).getTime()
      )
    : [];

  function handleRepoClick(repoId: number) {
    router.push(`/repos/${repoId}/tree`);
  }

  function handleIngest(repoId: number) {
    router.push(`/repos/new?repoId=${repoId}`);
  }

  // Loading state
  if (isLoading) {
    return <DashboardSkeleton />;
  }

  // Error state with retry
  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <AlertCircle className="h-12 w-12 text-destructive" />
        <h2 className="mt-4 text-lg font-semibold">Failed to load repositories</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          {error instanceof Error ? error.message : "Something went wrong"}
        </p>
        <Button onClick={() => refetch()} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  // Empty state
  if (sortedRepos.length === 0) {
    return (
      <div className="space-y-6">
        <DashboardHeader repoCount={0} onIngest={handleIngest} />
        <div className="flex flex-col items-center justify-center py-16">
          <FolderOpen className="h-12 w-12 text-muted-foreground" />
          <h2 className="mt-4 text-lg font-semibold">No repositories yet</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Ingest your first repository to get started with AI-powered code exploration.
          </p>
          <IngestDialog
            existingRepoCount={0}
            existingRepos={[]}
            onIngest={handleIngest}
            trigger={
              <Button className="mt-4">Ingest Your First Repository</Button>
            }
          />
        </div>
      </div>
    );
  }

  // Populated state
  return (
    <div className="space-y-6">
      <DashboardHeader
        repoCount={sortedRepos.length}
        repos={sortedRepos}
        onIngest={handleIngest}
      />
      <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        {sortedRepos.map((repo) => (
          <RepoCard
            key={repo.id}
            repository={repo}
            onClick={() => handleRepoClick(repo.id)}
          />
        ))}
      </div>
    </div>
  );
}

interface DashboardHeaderProps {
  repoCount: number;
  repos?: Repository[];
  onIngest: (repoId: number) => void;
}

function DashboardHeader({ repoCount, repos = [], onIngest }: DashboardHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          {repoCount === 0
            ? "Get started by ingesting a repository"
            : `${repoCount} ${repoCount === 1 ? "repository" : "repositories"}`}
        </p>
      </div>
      <IngestDialog
        existingRepoCount={repoCount}
        existingRepos={repos}
        onIngest={onIngest}
      />
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="h-8 w-40 animate-pulse rounded bg-gray-200" />
          <div className="h-4 w-24 animate-pulse rounded bg-gray-200" />
        </div>
        <div className="h-10 w-40 animate-pulse rounded bg-gray-200" />
      </div>
      {/* Cards skeleton */}
      <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="h-32 animate-pulse rounded-lg border bg-gray-100"
          />
        ))}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <AuthGuard>
      <DashboardContent />
    </AuthGuard>
  );
}
