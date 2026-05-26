// --- Language ---
export type LanguageCode = "en" | "es" | "fr" | "de" | "pt" | "ja" | "ko" | "zh";

// --- Repository Status ---
export type RepositoryStatus =
  | "cloning"
  | "extracting"
  | "parsing"
  | "summarizing"
  | "ready"
  | "partially_summarized"
  | "failed";

// --- Summary Status ---
export type SummaryStatus =
  | "completed"
  | "pending"
  | "failed"
  | "permanently_failed"
  | "not_applicable";

// --- Auth ---
export interface User {
  id: number;
  username: string;
  email: string;
  languagePreference: LanguageCode;
  avatarUrl: string | null;
}

export interface AuthSession {
  isAuthenticated: boolean;
  user: User | null;
}

// --- Sharing ---
export interface ShareInfo {
  token: string;
  url: string;
  isActive: boolean;
  createdAt: string;
}

// --- Repository ---
export interface Repository {
  id: number;
  name: string;
  sourceType: "github" | "zip";
  githubFullName: string | null;
  status: RepositoryStatus;
  fileCount: number;
  totalSizeBytes: number;
  ingestedAt: string; // ISO 8601
  updatedAt: string;
  shareInfo: ShareInfo | null;
}

// --- File Tree ---
export interface FileTreeNode {
  id: number;
  name: string;
  path: string;
  type: "file" | "directory";
  language: string | null;
  summaryPreview: string | null; // Truncated to 80 chars
  summaryStatus: SummaryStatus;
  children: FileTreeNode[] | null; // null for files, array for dirs
}

// --- File Detail ---
export interface FileSummary {
  text: string;
  status: SummaryStatus;
  language: LanguageCode;
  generatedAt: string | null;
  canRetry: boolean;
}

export interface BlockSummaryItem {
  id: number;
  name: string;
  kind: "function" | "class" | "method" | "module_construct";
  startLine: number;
  endLine: number;
  summaryText: string | null;
  summaryStatus: SummaryStatus;
}

export interface FileDetail {
  id: number;
  path: string;
  filename: string;
  language: string;
  summary: FileSummary | null;
  blocks: BlockSummaryItem[];
}

// --- Block Detail ---
export interface BlockDetail {
  id: number;
  name: string;
  kind: string;
  startLine: number;
  endLine: number;
  sourceCode: string;
  summary: {
    text: string;
    status: SummaryStatus;
    language: LanguageCode;
    generatedAt: string | null;
  } | null;
  parentBlockName: string | null;
}

// --- Progress ---
export interface ProgressReport {
  totalJobs: number;
  completed: number;
  pending: number;
  failed: number;
  status: RepositoryStatus;
}

// --- Search ---
export interface SearchResult {
  filePath: string;
  blockName: string | null;
  summaryExcerpt: string; // Up to 200 chars
  similarityRank: number;
  resultType: "file" | "block";
  fileId: number;
  blockId: number | null;
}

// --- Errors ---
export interface ApiError {
  status: number;
  message: string;
  detail?: string;
  code?: string;
}
