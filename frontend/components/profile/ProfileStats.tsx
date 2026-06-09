"use client";

import Link from "next/link";

interface ProfileStatsProps {
  slug: string;
  followerCount: number;
  followingCount: number;
}

/**
 * Displays follower and following counts, each linking to their list pages.
 */
export function ProfileStats({ slug, followerCount, followingCount }: ProfileStatsProps) {
  return (
    <div className="flex gap-6 text-sm">
      <Link href={`/${slug}/followers`} className="hover:underline">
        <span className="font-semibold">{followerCount}</span>{" "}
        <span className="text-muted-foreground">
          {followerCount === 1 ? "Follower" : "Followers"}
        </span>
      </Link>
      <Link href={`/${slug}/following`} className="hover:underline">
        <span className="font-semibold">{followingCount}</span>{" "}
        <span className="text-muted-foreground">Following</span>
      </Link>
    </div>
  );
}
