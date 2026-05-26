"use client";

import React, {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useState,
  ReactNode,
} from "react";
import type { AuthSession, User } from "@/lib/types/api";

// --- Types ---

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface AuthActions {
  login(): void;
  logout(): Promise<void>;
}

export type AuthContextValue = AuthState & AuthActions;

function getUserFromSessionPayload(payload: AuthSession | User): User | null {
  if ("isAuthenticated" in payload) {
    return payload.isAuthenticated ? payload.user : null;
  }

  return payload;
}

// --- Context ---

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// --- Provider ---

export function AuthContextProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = user !== null;

  // Check session on mount by calling GET /api/auth/me/
  useEffect(() => {
    let cancelled = false;

    async function checkSession() {
      try {
        const response = await fetch("/api/auth/me/", {
          credentials: "same-origin",
        });

        if (!cancelled) {
          if (response.ok) {
            const data: AuthSession | User = await response.json();
            setUser(getUserFromSessionPayload(data));
          } else {
            setUser(null);
          }
        }
      } catch {
        if (!cancelled) {
          setUser(null);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    checkSession();

    return () => {
      cancelled = true;
    };
  }, []);

  // Redirect through Django's social-auth flow. Django builds the GitHub
  // authorization URL with the registered backend callback and stores state.
  const login = useCallback(async () => {
    window.location.href = "/api/auth/github/";
  }, []);

  // POST /api/auth/logout/, clear state, redirect to /login
  const logout = useCallback(async () => {
    // Read CSRF token from cookie
    const csrfMatch = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
    const csrfToken = csrfMatch ? decodeURIComponent(csrfMatch[1]) : "";
    try {
      await fetch("/api/auth/logout/", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrfToken,
        },
      });
    } catch {
      // Even if the logout request fails, clear local state
    } finally {
      setUser(null);
      window.location.href = "/login";
    }
  }, []);

  const value: AuthContextValue = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// --- Hook ---

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthContextProvider");
  }
  return context;
}
