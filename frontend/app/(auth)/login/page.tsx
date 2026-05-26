"use client";

import { Github } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth/auth-context";

export default function LoginPage() {
  const { login } = useAuth();

  return (
    <div className="flex flex-col items-center space-y-8">
      {/* Branding */}
      <div className="flex flex-col items-center space-y-2">
        <div className="flex items-center space-x-2">
          <div className="h-10 w-10 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-xl font-bold text-primary-foreground">D</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">DevConn</h1>
        </div>
        <p className="text-center text-muted-foreground">
          AI-powered codebase explorer. Browse repositories, view AI-generated
          summaries, and search your code using natural language.
        </p>
      </div>

      {/* Login Card */}
      <div className="w-full rounded-lg border bg-card p-6 shadow-sm">
        <div className="flex flex-col items-center space-y-4">
          <h2 className="text-lg font-semibold">Sign in to continue</h2>
          <p className="text-sm text-muted-foreground text-center">
            Connect your GitHub account to get started with AI-powered code exploration.
          </p>
          <Button
            onClick={login}
            size="lg"
            className="w-full"
          >
            <Github className="mr-2 h-5 w-5" />
            Continue with GitHub
          </Button>
        </div>
      </div>
    </div>
  );
}
