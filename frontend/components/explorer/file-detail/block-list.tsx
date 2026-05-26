"use client";

import { Badge } from "@/components/ui/badge";
import type { BlockSummaryItem } from "@/lib/types/api";
import { Code2, Braces, Box, Layers } from "lucide-react";

interface BlockListProps {
  blocks: BlockSummaryItem[];
  onBlockSelect: (blockId: number) => void;
}

const kindIcons: Record<BlockSummaryItem["kind"], React.ElementType> = {
  function: Code2,
  class: Box,
  method: Braces,
  module_construct: Layers,
};

const kindLabels: Record<BlockSummaryItem["kind"], string> = {
  function: "Function",
  class: "Class",
  method: "Method",
  module_construct: "Module",
};

/**
 * Renders a list of code blocks with name, kind badge, and line range.
 * Each block is clickable to navigate to the block detail view.
 */
export function BlockList({ blocks, onBlockSelect }: BlockListProps) {
  if (blocks.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No code blocks found in this file.
      </p>
    );
  }

  return (
    <div className="space-y-1">
      {blocks.map((block) => {
        const Icon = kindIcons[block.kind] ?? Code2;

        return (
          <button
            key={block.id}
            onClick={() => onBlockSelect(block.id)}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-muted/50"
            aria-label={`View ${block.name} (${kindLabels[block.kind]}, lines ${block.startLine}-${block.endLine})`}
          >
            <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="flex-1 truncate font-medium">{block.name}</span>
            <Badge variant="secondary" className="shrink-0 text-xs">
              {kindLabels[block.kind]}
            </Badge>
            <span className="shrink-0 text-xs text-muted-foreground">
              L{block.startLine}–{block.endLine}
            </span>
          </button>
        );
      })}
    </div>
  );
}
