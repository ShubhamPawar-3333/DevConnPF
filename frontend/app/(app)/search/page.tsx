"use client";

import { useState } from "react";
import { Search, UserCircle2 } from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { useSearchProfiles } from "@/lib/hooks/use-profiles";
import { useDebounce } from "@/lib/hooks/use-debounce";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [skillTag, setSkillTag] = useState("");
  const [page, setPage] = useState(1);

  const debouncedQuery = useDebounce(query, 300);

  const { data, isLoading, isError } = useSearchProfiles(
    debouncedQuery,
    skillTag || undefined,
    page
  );

  const queryTooLong = query.length > 200;

  function handleQueryChange(val: string) {
    setQuery(val);
    setPage(1);
  }

  function handleSkillTagClear() {
    setSkillTag("");
    setPage(1);
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 py-8 px-4">
      <h1 className="text-2xl font-bold">Discover Developers</h1>

      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          className="pl-9"
          value={query}
          onChange={(e) => handleQueryChange(e.target.value)}
          placeholder="Search by name, skills, or bio..."
          aria-label="Search developers"
        />
      </div>

      {queryTooLong && (
        <p className="text-xs text-destructive">Search query must be 200 characters or fewer.</p>
      )}

      {skillTag && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Filtering by skill:</span>
          <Badge variant="secondary">{skillTag}</Badge>
          <Button variant="ghost" size="sm" onClick={handleSkillTagClear}>×</Button>
        </div>
      )}

      {/* Results */}
      {debouncedQuery && !queryTooLong && (
        <>
          {isLoading && (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-start gap-3 animate-pulse">
                  <div className="h-12 w-12 rounded-full bg-gray-200 shrink-0" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-40 rounded bg-gray-200" />
                    <div className="h-3 w-64 rounded bg-gray-200" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {isError && (
            <p className="text-sm text-destructive">Search failed. Please try again.</p>
          )}

          {!isLoading && !isError && data && (
            <>
              <p className="text-sm text-muted-foreground">{data.count} result{data.count !== 1 ? "s" : ""}</p>

              {data.results.length === 0 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">
                  No developers found matching &ldquo;{debouncedQuery}&rdquo;.
                </p>
              ) : (
                <ul className="divide-y">
                  {data.results.map((profile) => (
                    <li key={profile.slug} className="py-4">
                      <Link href={`/${profile.slug}`} className="flex items-start gap-3 hover:opacity-80 transition-opacity">
                        {profile.avatar_url ? (
                          <Image src={profile.avatar_url} alt={profile.display_name} width={48} height={48} className="h-12 w-12 rounded-full object-cover shrink-0" unoptimized />
                        ) : (
                          <UserCircle2 className="h-12 w-12 text-muted-foreground shrink-0" />
                        )}
                        <div className="flex-1 min-w-0 space-y-1">
                          <div className="flex items-center gap-2">
                            <p className="font-semibold text-sm">{profile.display_name}</p>
                            <p className="text-xs text-muted-foreground">@{profile.slug}</p>
                          </div>
                          {profile.bio && (
                            <p className="text-xs text-muted-foreground line-clamp-2">{profile.bio}</p>
                          )}
                          {profile.skill_tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {profile.skill_tags.slice(0, 5).map((tag) => (
                                <button
                                  key={tag}
                                  onClick={(e) => { e.preventDefault(); setSkillTag(tag); setPage(1); }}
                                  className="rounded-full border px-2 py-0.5 text-xs hover:bg-secondary transition-colors"
                                >
                                  {tag}
                                </button>
                              ))}
                              {profile.skill_tags.length > 5 && (
                                <span className="text-xs text-muted-foreground">+{profile.skill_tags.length - 5}</span>
                              )}
                            </div>
                          )}
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}

              {/* Pagination */}
              {data.count > 20 && (
                <div className="flex items-center justify-between pt-4">
                  <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">Page {page}</span>
                  <Button variant="outline" size="sm" disabled={data.results.length < 20} onClick={() => setPage((p) => p + 1)}>
                    Next
                  </Button>
                </div>
              )}
            </>
          )}
        </>
      )}

      {!debouncedQuery && (
        <div className="flex flex-col items-center py-16 text-center text-muted-foreground">
          <Search className="h-12 w-12 mb-3" />
          <p className="text-sm">Search for developers by name, bio, or skills.</p>
        </div>
      )}
    </div>
  );
}
