"use client";

import { useRouter, useParams } from "next/navigation";
import { SearchPanel } from "@/components/explorer/search/search-panel";
import type { SearchResult } from "@/lib/types/api";

export default function SearchPage() {
  const router = useRouter();
  const params = useParams();
  const repoId = Number(params.id);

  const handleResultSelect = (result: SearchResult) => {
    if (result.resultType === "block" && result.blockId != null) {
      router.push(`/repos/${repoId}/blocks/${result.blockId}`);
    } else {
      router.push(`/repos/${repoId}/files/${result.fileId}`);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">Search</h1>
      <SearchPanel repoId={repoId} onResultSelect={handleResultSelect} />
    </div>
  );
}
