"use client";

import { useParams } from "next/navigation";
import { BlockDetailPanel } from "@/components/explorer/block-detail/block-detail-panel";

/**
 * Block detail page — renders the BlockDetailPanel.
 * Requirement: 8.1 (block detail display with name, kind, lines, code, summary)
 */
export default function BlockDetailPage() {
  const params = useParams();
  const repoId = Number(params.id);
  const blockId = Number(params.blockId);

  return (
    <BlockDetailPanel
      repoId={repoId}
      blockId={blockId}
    />
  );
}
