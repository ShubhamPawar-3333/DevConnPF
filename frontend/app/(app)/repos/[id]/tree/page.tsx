"use client";

import { useParams, useRouter } from "next/navigation";
import { FileTree } from "@/components/explorer/file-tree";

/**
 * Tree page — renders the FileTree component with navigation handlers.
 * Requirements: 5.1 (file tree display), 5.6 (file click navigates to detail)
 */
export default function TreePage() {
  const params = useParams();
  const router = useRouter();
  const repoId = Number(params.id);

  const handleFileSelect = (fileId: number) => {
    router.push(`/repos/${repoId}/files/${fileId}`);
  };

  const handleBlockSelect = (blockId: number) => {
    router.push(`/repos/${repoId}/blocks/${blockId}`);
  };

  return (
    <div className="h-full">
      <FileTree
        repoId={repoId}
        onFileSelect={handleFileSelect}
        onBlockSelect={handleBlockSelect}
      />
    </div>
  );
}
