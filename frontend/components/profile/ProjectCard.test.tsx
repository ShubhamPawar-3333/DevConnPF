/**
 * Task 21.1 — Component tests for ProjectCard
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ProjectCard } from "./ProjectCard";
import type { ProjectEntry } from "@/lib/types/profiles";

const mockProject: ProjectEntry = {
  id: 1,
  repository_name: "my-repo",
  custom_description: "A great project",
  primary_language: "TypeScript",
  explorer_link: "/repos/1",
  display_order: 0,
  added_at: "2024-01-01T00:00:00Z",
};

describe("ProjectCard", () => {
  it("renders project name", () => {
    render(<ProjectCard project={mockProject} />);
    expect(screen.getByText("my-repo")).toBeInTheDocument();
  });

  it("renders custom description", () => {
    render(<ProjectCard project={mockProject} />);
    expect(screen.getByText("A great project")).toBeInTheDocument();
  });

  it("renders language badge", () => {
    render(<ProjectCard project={mockProject} />);
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
  });

  it("renders explorer link with correct href", () => {
    render(<ProjectCard project={mockProject} />);
    const link = screen.getByRole("link", { name: /explore/i });
    expect(link).toHaveAttribute("href", "/repos/1");
  });

  it("handles missing optional fields gracefully", () => {
    const minimal: ProjectEntry = {
      ...mockProject,
      custom_description: null,
      primary_language: null,
    };
    render(<ProjectCard project={minimal} />);
    expect(screen.getByText("my-repo")).toBeInTheDocument();
  });
});
