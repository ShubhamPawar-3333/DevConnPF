"use client";

import Image from "next/image";
import Link from "next/link";
import { UserCircle2 } from "lucide-react";
import type { Profile } from "@/lib/types/profiles";

interface SearchResultCardProps {
  profile: Profile;
  /** Optional callback when a skill tag badge is clicked for filtering. */
  onTagClick?: (tag: string) => void;
}

/**
 * Standalone card for a single search result.
 *
 * Displays: avatar (or UserCircle2 fallback), display_name, @slug,
 * bio snippet (line-clamp-2), and up to 5 clickable skill tags.
 * The whole card links to `/{profile.slug}`.
 */
export function SearchResultCard({ profile, onTagClick }: SearchResultCardProps) {
  return (
    <article className="py-4">
      <Link
        href={`/${profile.slug}`}
        className="flex items-start gap-3 hover:opacity-80 transition-opacity"
      >
        {/* Avatar */}
        {profile.avatar_url ? (
          <Image
            src={profile.avatar_url}
            alt={`${profile.display_name} avatar`}
            width={48}
            height={48}
            className="h-12 w-12 rounded-full object-cover shrink-0"
            unoptimized
          />
        ) : (
          <UserCircle2 className="h-12 w-12 text-muted-foreground shrink-0" />
        )}

        {/* Details */}
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-center gap-2">
            <p className="font-semibold text-sm">{profile.display_name}</p>
            <p className="text-xs text-muted-foreground">@{profile.slug}</p>
          </div>

          {profile.bio && (
            <p className="text-xs text-muted-foreground line-clamp-2">
              {profile.bio}
            </p>
          )}

          {profile.skill_tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {profile.skill_tags.slice(0, 5).map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    onTagClick?.(tag);
                  }}
                  className="rounded-full border px-2 py-0.5 text-xs hover:bg-secondary transition-colors"
                  aria-label={`Filter by ${tag}`}
                >
                  {tag}
                </button>
              ))}
              {profile.skill_tags.length > 5 && (
                <span className="text-xs text-muted-foreground self-center">
                  +{profile.skill_tags.length - 5}
                </span>
              )}
            </div>
          )}
        </div>
      </Link>
    </article>
  );
}
