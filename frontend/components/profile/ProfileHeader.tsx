"use client";

import Image from "next/image";
import { MapPin, Globe, UserCircle2 } from "lucide-react";
import { ProfileStats } from "./ProfileStats";
import type { Profile } from "@/lib/types/profiles";

interface ProfileHeaderProps {
  profile: Profile;
  /** Slot for a follow/unfollow button rendered by the parent. */
  action?: React.ReactNode;
}

/**
 * Top section of a profile page: avatar, name, bio, location, website, stats.
 */
export function ProfileHeader({ profile, action }: ProfileHeaderProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:gap-6">
      {/* Avatar */}
      <div className="shrink-0">
        {profile.avatar_url ? (
          <Image
            src={profile.avatar_url}
            alt={`${profile.display_name} avatar`}
            width={96}
            height={96}
            className="h-24 w-24 rounded-full object-cover border"
            unoptimized
          />
        ) : (
          <UserCircle2 className="h-24 w-24 text-muted-foreground" />
        )}
      </div>

      {/* Info */}
      <div className="flex-1 space-y-2">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold leading-tight">
              {profile.display_name}
            </h1>
            <p className="text-sm text-muted-foreground">@{profile.slug}</p>
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>

        {profile.bio && (
          <p className="text-sm text-foreground max-w-xl">{profile.bio}</p>
        )}

        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
          {profile.location && (
            <span className="flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5" />
              {profile.location}
            </span>
          )}
          {profile.website_url && (
            <a
              href={profile.website_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-primary hover:underline"
            >
              <Globe className="h-3.5 w-3.5" />
              {profile.website_url.replace(/^https?:\/\//, "")}
            </a>
          )}
        </div>

        <ProfileStats
          slug={profile.slug}
          followerCount={profile.follower_count}
          followingCount={profile.following_count}
        />
      </div>
    </div>
  );
}
