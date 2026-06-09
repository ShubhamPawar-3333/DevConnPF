"use client";

import { Trash2, GripVertical } from "lucide-react";
import { useRemoveProject, useReorderProjects } from "@/lib/hooks/use-profiles";
import { Button } from "@/components/ui/button";
import type { ProjectEntry } from "@/lib/types/profiles";

interface ProjectManagementPanelProps {
  projects: ProjectEntry[];
  /** Called when user wants to open the add-project dialog */
  onAddClick: () => void;
}

/**
 * Displays the current project list with remove buttons and project count.
 * Drag-to-reorder is indicated visually; reorder is saved on drop.
 * (Full DnD library integration kept optional — basic reorder via buttons shown here.)
 */
export function ProjectManagementPanel({ projects, onAddClick }: ProjectManagementPanelProps) {
  const { mutate: removeProject } = useRemoveProject();
  const { mutate: reorder } = useReorderProjects();

  function moveUp(index: number) {
    if (index === 0) return;
    const reordered = [...projects];
    [reordered[index - 1], reordered[index]] = [reordered[index], reordered[index - 1]];
    reorder({
      projects: reordered.map((p, i) => ({ id: p.id, display_order: i })),
    });
  }

  function moveDown(index: number) {
    if (index === projects.length - 1) return;
    const reordered = [...projects];
    [reordered[index], reordered[index + 1]] = [reordered[index + 1], reordered[index]];
    reorder({
      projects: reordered.map((p, i) => ({ id: p.id, display_order: i })),
    });
  }

  return (
    <div className="space-y-4">
      {/* Header with count and add button */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {projects.length}/50 projects
        </p>
        <Button
          size="sm"
          onClick={onAddClick}
          disabled={projects.length >= 50}
        >
          + Add Project
        </Button>
      </div>

      {/* Project list */}
      {projects.length === 0 ? (
        <p className="text-sm text-muted-foreground py-6 text-center">
          No projects yet. Add one to showcase your work.
        </p>
      ) : (
        <ul className="space-y-2">
          {projects.map((project, index) => (
            <li
              key={project.id}
              className="flex items-center gap-3 rounded-md border bg-card px-4 py-3"
            >
              {/* Drag handle placeholder */}
              <GripVertical className="h-4 w-4 text-muted-foreground shrink-0 cursor-grab" aria-hidden />

              {/* Project info */}
              <div className="flex-1 min-w-0">
                <p className="truncate font-medium text-sm">{project.repository_name}</p>
                {project.custom_description && (
                  <p className="truncate text-xs text-muted-foreground">
                    {project.custom_description}
                  </p>
                )}
              </div>

              {/* Reorder buttons */}
              <div className="flex gap-1 shrink-0">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0"
                  onClick={() => moveUp(index)}
                  disabled={index === 0}
                  aria-label="Move up"
                >
                  ↑
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0"
                  onClick={() => moveDown(index)}
                  disabled={index === projects.length - 1}
                  aria-label="Move down"
                >
                  ↓
                </Button>
              </div>

              {/* Remove button */}
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 shrink-0"
                onClick={() => removeProject(project.id)}
                aria-label={`Remove ${project.repository_name}`}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
