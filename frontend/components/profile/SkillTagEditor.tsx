"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

interface SkillTagEditorProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  error?: string;
}

/**
 * Editable skill tag field: add via input + Enter or button, remove by clicking ×.
 * Enforces max 20 tags, each max 50 chars.
 */
export function SkillTagEditor({ tags, onChange, error }: SkillTagEditorProps) {
  const [input, setInput] = useState("");
  const [inputError, setInputError] = useState("");

  function add() {
    const tag = input.trim();
    if (!tag) return;
    if (tag.length > 50) {
      setInputError("Tag must be 50 characters or fewer.");
      return;
    }
    if (tags.length >= 20) {
      setInputError("Maximum 20 skill tags allowed.");
      return;
    }
    if (tags.includes(tag)) {
      setInputError("Tag already added.");
      return;
    }
    onChange([...tags, tag]);
    setInput("");
    setInputError("");
  }

  function remove(tag: string) {
    onChange(tags.filter((t) => t !== tag));
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label>Skills</Label>
        <span className="text-xs text-muted-foreground">{tags.length}/20</span>
      </div>

      <div className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => { setInput(e.target.value); setInputError(""); }}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }}
          placeholder="e.g. Python, TypeScript, Rust"
          maxLength={50}
          aria-label="Add skill tag"
        />
        <Button type="button" variant="outline" onClick={add}>Add</Button>
      </div>

      {(inputError || error) && (
        <p className="text-xs text-destructive">{inputError || error}</p>
      )}

      {tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {tags.map((tag) => (
            <Badge key={tag} variant="secondary" className="gap-1 pl-3 pr-2">
              {tag}
              <button
                type="button"
                onClick={() => remove(tag)}
                className="rounded-full hover:bg-destructive/20 p-0.5 transition-colors"
                aria-label={`Remove ${tag}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
