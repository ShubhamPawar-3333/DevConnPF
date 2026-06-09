"use client";

import Link from "next/link";
import { ExternalLink, Code2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ProjectEntry } from "@/lib/types/profiles";

interface ProjectCardProps {
  project: ProjectEntry;
}

/**
 * Displays a single project entry with name, description, language badge,
 * and a link to the AI Codebase Explorer.
 */
export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-1 min-w-0">
            <div className="flex items-center gap-2">
              <Code2 className="h-4 w-4 shrink-0 text-muted-foreground" />
              <h3 className="truncate font-semibold text-sm">
                {project.repository_name}
              </h3>
              {project.primary_language && (
                <Badge variant="outline" className="shrink-0 text-xs">
                  {project.primary_language}
                </Badge>
              )}
            </div>
            {project.custom_description && (
              <p className="text-sm text-muted-foreground line-clamp-2">
                {project.custom_description}
              </p>
            )}
          </div>

          <Link
            href={project.explorer_link}
            className="shrink-0 flex items-center gap-1 text-xs text-primary hover:underline"
            aria-label={`Explore ${project.repository_name} codebase`}
          >
            <ExternalLink className="h-3.5 w-3.5" />
            <span>Explore</span>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
