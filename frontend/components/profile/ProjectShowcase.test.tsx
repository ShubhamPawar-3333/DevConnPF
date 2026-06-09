/**
 * Task 21.1 — Component tests for ProjectShowcase
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ProjectShowcase } from "./ProjectShowcase";
import type { ProjectEntry } from "@/lib/types/profiles";

const mockProjects: ProjectEntry[] = [
  {
    id: 1,
    repository_name: "repo-one",
    custom_description: "First project",
    primary_language: "Python",
    explorer_link: "/repos/1",
    display_order: 0,
    added_at: "2024-01-01T00:00:00Z",
  },
  {
    id: 2,
    repository_name: "repo-two",
    custom_description: null,
    primary_language: "TypeScript",
    explorer_link: "/repos/2",
    display_order: 1,
    added_at: "2024-01-02T00:00:00Z",
  },
];

describe("ProjectShowcase", () => {
  it("renders all project cards", () => {
    render(<ProjectShowcase projects={mockProjects} />);
    expect(screen.getByText("repo-one")).toBeInTheDocument();
    expect(screen.getByText("repo-two")).toBeInTheDocument();
  });

  it("shows empty state when no projects", () => {
    render(<ProjectShowcase projects={[]} />);
    expect(screen.getByText(/no projects yet/i)).toBeInTheDocument();
  });
});
