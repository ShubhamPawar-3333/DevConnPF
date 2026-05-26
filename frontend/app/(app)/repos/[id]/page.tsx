import { redirect } from "next/navigation";

/**
 * Repository root page — redirects to the tree view.
 * Requirement 5.1: navigating to a repository shows the file tree.
 */
export default function RepoPage({ params }: { params: { id: string } }) {
  redirect(`/repos/${params.id}/tree`);
}
