import type { SearchResult } from "./api";

export interface FileTreeState {
  expandedPaths: Set<string>;
  selectedFileId: number | null;
  selectedBlockId: number | null;
}

export interface SearchState {
  query: string;
  isSearching: boolean;
  results: SearchResult[];
  hasSearched: boolean;
}

export interface IngestionState {
  step: "select" | "uploading" | "processing" | "complete" | "error";
  repositoryId: number | null;
  error: string | null;
}
