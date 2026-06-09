"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { AuthGuard } from "@/lib/auth/auth-guard";
import { useMyProfile, useRemoveProject, useAddProject } from "@/lib/hooks/use-profiles";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Repository } from "@/lib/types/api";

function ProjectManagementContent() {
  const { data: profile, isLoading } = useMyProfile();
  const { mutate: removeProject } = useRemoveProject();
  const { mutate: addProject, isPending: adding } = useAddProject();

  const { data: repos } = useQuery<Repository[]>({
    queryKey: ["repositories"],
    queryFn: () => apiClient.get<Repository[]>("/api/repositories/"),
  });

  const [selectedRepoId, setSelectedRepoId] = useState<number | "">("");
  const [description, setDescription] = useState("");
  const [addError, setAddError] = useState("");

  if (isLoading || !profile) {
    return <div className="animate-pulse h-64 rounded bg-gray-100" />;
  }

  const projectCount = profile.projects.length;
  const addedRepoIds = new Set(profile.projects.map((p) => {
    // extract repo id from explorer_link e.g. /repos/5
    const match = p.explorer_link.match(/\/repos\/(\d+)/);
    return match ? Number(match[1]) : -1;
  }));

  function handleAdd() {
    if (!selectedRepoId) return;
    setAddError("");
    addProject(
      { repository_id: Number(selectedRepoId), custom_description: description || null },
      {
        onSuccess: () => {
          setSelectedRepoId("");
          setDescription("");
        },
        onError: (err: unknown) => {
          const apiErr = err as { message?: string };
          setAddError(apiErr?.message ?? "Failed to add project.");
        },
      }
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8 py-8 px-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Manage Projects</h1>
        <span className="text-sm text-muted-foreground">{projectCount}/50 projects</span>
      </div>

      {/* Current projects */}
      <section>
        <h2 className="mb-3 font-semibold">Your Projects</h2>
        {profile.projects.length === 0 ? (
          <p className="text-sm text-muted-foreground">No projects added yet.</p>
        ) : (
          <ul className="space-y-2">
            {profile.projects.map((project) => (
              <li key={project.id} className="flex items-center justify-between rounded-md border px-4 py-3">
                <div>
                  <p className="font-medium text-sm">{project.repository_name}</p>
                  {project.custom_description && (
                    <p className="text-xs text-muted-foreground">{project.custom_description}</p>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => removeProject(project.id)}
                  aria-label={`Remove ${project.repository_name}`}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Add project */}
      {projectCount < 50 && repos && repos.length > 0 && (
        <section>
          <h2 className="mb-3 font-semibold">Add Project</h2>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label htmlFor="repo-select">Repository</Label>
              <select
                id="repo-select"
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={selectedRepoId}
                onChange={(e) => setSelectedRepoId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">Select a repository...</option>
                {repos
                  .filter((r) => !addedRepoIds.has(r.id))
                  .map((r) => (
                    <option key={r.id} value={r.id}>{r.name}</option>
                  ))}
              </select>
            </div>

            <div className="space-y-1">
              <Label htmlFor="proj-desc">Custom description <span className="text-muted-foreground">(optional)</span></Label>
              <Input
                id="proj-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="A short description for your profile..."
                maxLength={300}
              />
              <p className="text-xs text-muted-foreground text-right">{description.length}/300</p>
            </div>

            {addError && <p className="text-xs text-destructive">{addError}</p>}

            <Button onClick={handleAdd} disabled={!selectedRepoId || adding}>
              {adding ? "Adding..." : "Add Project"}
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}

export default function ProjectManagementPage() {
  return (
    <AuthGuard>
      <ProjectManagementContent />
    </AuthGuard>
  );
}
