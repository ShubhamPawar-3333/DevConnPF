"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useMyProfile } from "@/lib/hooks/use-profiles";
import { useAuth } from "@/lib/auth/auth-context";

/**
 * Redirects authenticated users who have not yet completed onboarding
 * to /onboarding when they try to access profile-dependent pages.
 *
 * Mount this inside any authenticated layout to enforce onboarding.
 */
export function OnboardingRedirect() {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const {
    data: profile,
    isLoading: profileLoading,
    isError,
  } = useMyProfile({ enabled: isAuthenticated && !authLoading });

  useEffect(() => {
    // Skip if still loading or not authenticated
    if (authLoading || profileLoading || !isAuthenticated) return;
    // Skip if already on the onboarding page
    if (pathname === "/onboarding") return;
    // If there's no profile (404 or error), redirect to onboarding
    if (isError && !profile) {
      router.replace("/onboarding");
    }
  }, [authLoading, profileLoading, isAuthenticated, isError, profile, pathname, router]);

  return null;
}
