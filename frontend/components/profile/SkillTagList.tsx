"use client";

import { Badge } from "@/components/ui/badge";

interface SkillTagListProps {
  tags: string[];
}

/**
 * Renders skill tags as labeled badges. Shows an empty state if no tags.
 */
export function SkillTagList({ tags }: SkillTagListProps) {
  if (tags.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No skills listed yet.</p>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {tags.map((tag) => (
        <Badge key={tag} variant="secondary" className="text-xs">
          {tag}
        </Badge>
      ))}
    </div>
  );
}
