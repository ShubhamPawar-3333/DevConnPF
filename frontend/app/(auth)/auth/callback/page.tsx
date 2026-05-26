"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { getPostLoginRedirectUrl } from "@/lib/auth/auth-guard";

type CallbackState = "processing" | "success" | "error";

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<AuthCallbackLoading />}>
      <AuthCallbackContent />
    </Suspense>
  );
}

function AuthCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [state, setState] = useState<CallbackState>("processing");
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Prevent double-processing in React strict mode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const code = searchParams.get("code");
    const returnedState = searchParams.get("state");
    const error = searchParams.get("error");

    // If GitHub returned an error (e.g., user denied authorization)
    if (error) {
      router.replace(`/auth/error?error=${encodeURIComponent(error)}`);
      return;
    }

    // If no authorization code is present, redirect to error
    if (!code) {
      router.replace("/auth/error?error=missing_code");
      return;
    }

    async function exchangeCode() {
      try {
        const response = await fetch("/api/auth/github/callback/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            code,
            state: returnedState,
          }),
        });

        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          const errorReason =
            body.error || body.detail || "callback_failed";
          router.replace(
            `/auth/error?error=${encodeURIComponent(errorReason)}`
          );
          return;
        }

        // Session established successfully
        setState("success");

        // Redirect to stored URL or dashboard within 3 seconds
        const redirectUrl = getPostLoginRedirectUrl() || "/dashboard";

        // Small delay to show success state, then redirect
        setTimeout(() => {
          router.replace(redirectUrl);
        }, 500);
      } catch {
        // Network error
        router.replace("/auth/error?error=network_error");
      }
    }

    exchangeCode();
  }, [searchParams, router]);

  return (
    <div className="flex flex-col items-center space-y-6">
      {state === "processing" && (
        <>
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
          <div className="flex flex-col items-center space-y-2 text-center">
            <h1 className="text-xl font-semibold">Signing you in...</h1>
            <p className="text-sm text-muted-foreground">
              Please wait while we complete your authentication.
            </p>
          </div>
        </>
      )}

      {state === "success" && (
        <>
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
            <svg
              className="h-8 w-8 text-green-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <div className="flex flex-col items-center space-y-2 text-center">
            <h1 className="text-xl font-semibold">Authentication successful</h1>
            <p className="text-sm text-muted-foreground">
              Redirecting you to the dashboard...
            </p>
          </div>
        </>
      )}
    </div>
  );
}

function AuthCallbackLoading() {
  return (
    <div className="flex flex-col items-center space-y-6">
      <Loader2 className="h-12 w-12 animate-spin text-primary" />
      <div className="flex flex-col items-center space-y-2 text-center">
        <h1 className="text-xl font-semibold">Signing you in...</h1>
        <p className="text-sm text-muted-foreground">
          Please wait while we complete your authentication.
        </p>
      </div>
    </div>
  );
}
