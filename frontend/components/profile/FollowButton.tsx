"use client";

import { UserPlus, UserCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useFollow, useUnfollow } from "@/lib/hooks/use-profiles";

interface FollowButtonProps {
  /** The slug of the profile to follow/unfollow. */
  slug: string;
  /** Whether the authenticated user is currently following this profile. */
  isFollowing: boolean;
  /** If true, the button is hidden (user is viewing their own profile). */
  isOwnProfile: boolean;
}

/**
 * Follow / unfollow toggle button.
 *
 * - Hidden when `isOwnProfile` is true.
 * - Shows "Follow" when not following, "Following" when already following.
 * - Calls the appropriate mutation on click.
 * - Disabled while a mutation is in progress.
 */
export function FollowButton({ slug, isFollowing, isOwnProfile }: FollowButtonProps) {
  const followMutation = useFollow(slug);
  const unfollowMutation = useUnfollow(slug);

  // Don't render anything for the profile owner
  if (isOwnProfile) return null;

  const isPending = followMutation.isPending || unfollowMutation.isPending;

  function handleClick() {
    if (isPending) return;
    if (isFollowing) {
      unfollowMutation.mutate();
    } else {
      followMutation.mutate();
    }
  }

  return (
    <Button
      variant={isFollowing ? "outline" : "default"}
      size="sm"
      onClick={handleClick}
      disabled={isPending}
      aria-label={isFollowing ? `Unfollow ${slug}` : `Follow ${slug}`}
    >
      {isFollowing ? (
        <>
          <UserCheck className="mr-1.5 h-4 w-4" />
          {isPending ? "Unfollowing…" : "Following"}
        </>
      ) : (
        <>
          <UserPlus className="mr-1.5 h-4 w-4" />
          {isPending ? "Following…" : "Follow"}
        </>
      )}
    </Button>
  );
}
