/**
 * Task 21.1 — Component tests for SkillTagList
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SkillTagList } from "./SkillTagList";

describe("SkillTagList", () => {
  it("renders all tags as badges", () => {
    render(<SkillTagList tags={["Python", "Django", "React"]} />);
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("Django")).toBeInTheDocument();
    expect(screen.getByText("React")).toBeInTheDocument();
  });

  it("shows empty state when no tags", () => {
    render(<SkillTagList tags={[]} />);
    expect(screen.getByText(/no skills listed/i)).toBeInTheDocument();
  });

  it("renders up to 20 tags without truncation", () => {
    const tags = Array.from({ length: 20 }, (_, i) => `Tag${i}`);
    render(<SkillTagList tags={tags} />);
    tags.forEach((tag) => expect(screen.getByText(tag)).toBeInTheDocument());
  });
});
