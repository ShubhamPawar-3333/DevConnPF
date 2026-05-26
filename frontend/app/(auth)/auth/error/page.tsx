"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

const ERROR_MESSAGES: Record<string, string> = {
  authorization_denied: "You denied the authorization request.",
  access_denied: "Access was denied by GitHub.",
  invalid_state: "The request could not be verified. Please try again.",
  server_error: "An unexpected error occurred on the server.",
};

function getErrorMessage(error: string | null): string {
  if (!error) {
    return "An unknown error occurred during authentication.";
  }
  return ERROR_MESSAGES[error] || `Authentication failed: ${error}`;
}

export default function AuthErrorPage() {
  return (
    <Suspense fallback={<AuthErrorContent error={null} />}>
      <AuthErrorSearchParams />
    </Suspense>
  );
}

function AuthErrorSearchParams() {
  const searchParams = useSearchParams();
  const error = searchParams.get("error");
  return <AuthErrorContent error={error} />;
}

function AuthErrorContent({ error }: { error: string | null }) {
  const errorMessage = getErrorMessage(error);

  return (
    <div className="flex flex-col items-center space-y-6">
      {/* Error Icon */}
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
        <AlertCircle className="h-8 w-8 text-destructive" />
      </div>

      {/* Error Message */}
      <div className="flex flex-col items-center space-y-2 text-center">
        <h1 className="text-2xl font-semibold">Authentication Error</h1>
        <p className="text-muted-foreground">{errorMessage}</p>
      </div>

      {/* Try Again */}
      <Button asChild>
        <Link href="/login">Try again</Link>
      </Button>
    </div>
  );
}
