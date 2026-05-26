"use client";

import { useParams, useRouter } from "next/navigation";
import { FileDetailPanel } from "@/components/explorer/file-detail/file-detail-panel";

/**
 * File detail page — renders the FileDetailPanel with block navigation.
 * Requirements: 6.1 (file detail display), 6.5 (block click navigates to block detail)
 */
export default function FileDetailPage() {
  const params = useParams();
  const router = useRouter();
  const repoId = Number(params.id);
  const fileId = Number(params.fileId);

  const handleBlockSelect = (blockId: number) => {
    router.push(`/repos/${repoId}/blocks/${blockId}`);
  };

  return (
    <FileDetailPanel
      repoId={repoId}
      fileId={fileId}
      onBlockSelect={handleBlockSelect}
    />
  );
}
