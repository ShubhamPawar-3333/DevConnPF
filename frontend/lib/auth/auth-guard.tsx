"use client";

import React, { useEffect, useRef } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "./auth-context";

const AUTH_TIMEOUT_MS = 10_000; // 10 seconds

/**
 * AuthGuard protects routes requiring authentication.
 *
 * Behavior:
 * - Shows a loading skeleton while auth state is being determined
 * - Redirects to /login if user is not authenticated (stores requested URL)
 * - Times out after 10s if auth check doesn't complete → redirect to login with error
 * - Renders children if authenticated
 * - After login, redirects to the originally requested URL
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasRedirected = useRef(false);

  // Timeout: if auth check doesn't complete within 10s, redirect to login
  useEffect(() => {
    if (isLoading) {
      timeoutRef.current = setTimeout(() => {
        if (!hasRedirected.current) {
          hasRedirected.current = true;
          // Store the requested URL for post-login redirect
          if (typeof window !== "undefined") {
            sessionStorage.setItem("auth_redirect_url", pathname);
          }
          router.replace("/login?error=timeout");
        }
      }, AUTH_TIMEOUT_MS);
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [isLoading, pathname, router]);

  // Redirect unauthenticated users to login
  useEffect(() => {
    if (!isLoading && !isAuthenticated && !hasRedirected.current) {
      hasRedirected.current = true;
      // Store the requested URL for post-login redirect
      if (typeof window !== "undefined") {
        sessionStorage.setItem("auth_redirect_url", pathname);
      }
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, pathname, router]);

  // Show loading skeleton while auth is loading
  if (isLoading) {
    return <AuthLoadingSkeleton />;
  }

  // Not authenticated — render nothing while redirect happens
  if (!isAuthenticated) {
    return null;
  }

  // Authenticated — render children
  return <>{children}</>;
}

/**
 * Loading skeleton displayed while auth state is being determined.
 * Matches the general layout dimensions to minimize CLS.
 */
function AuthLoadingSkeleton() {
  return (
    <div className="flex min-h-screen flex-col" aria-busy="true" aria-label="Loading">
      {/* Header skeleton */}
      <div className="h-16 border-b border-gray-200 bg-white">
        <div className="flex h-full items-center justify-between px-6">
          <div className="h-6 w-32 animate-pulse rounded bg-gray-200" />
          <div className="h-8 w-8 animate-pulse rounded-full bg-gray-200" />
        </div>
      </div>

      {/* Content skeleton */}
      <div className="flex flex-1">
        {/* Sidebar skeleton */}
        <div className="hidden w-64 border-r border-gray-200 bg-white p-4 md:block">
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-8 animate-pulse rounded bg-gray-200" />
            ))}
          </div>
        </div>

        {/* Main content skeleton */}
        <div className="flex-1 p-6">
          <div className="space-y-4">
            <div className="h-8 w-48 animate-pulse rounded bg-gray-200" />
            <div className="h-4 w-full animate-pulse rounded bg-gray-200" />
            <div className="h-4 w-3/4 animate-pulse rounded bg-gray-200" />
            <div className="h-4 w-1/2 animate-pulse rounded bg-gray-200" />
            <div className="mt-6 h-32 w-full animate-pulse rounded bg-gray-200" />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Utility to get the stored redirect URL after successful login.
 * Call this after authentication succeeds to redirect to the originally requested page.
 */
export function getPostLoginRedirectUrl(): string | null {
  if (typeof window === "undefined") return null;
  const url = sessionStorage.getItem("auth_redirect_url");
  if (url) {
    sessionStorage.removeItem("auth_redirect_url");
  }
  return url;
}
