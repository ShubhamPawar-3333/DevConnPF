"use client";

import { FolderOpen } from "lucide-react";
import { ProjectCard } from "./ProjectCard";
import type { ProjectEntry } from "@/lib/types/profiles";

interface ProjectShowcaseProps {
  projects: ProjectEntry[];
}

/**
 * Container that renders the list of project cards in display order,
 * or an empty state if no projects.
 */
export function ProjectShowcase({ projects }: ProjectShowcaseProps) {
  if (projects.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <FolderOpen className="h-10 w-10 text-muted-foreground" />
        <p className="mt-2 text-sm text-muted-foreground">No projects yet.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-1 md:grid-cols-2">
      {projects.map((project) => (
        <ProjectCard key={project.id} project={project} />
      ))}
    </div>
  );
}
