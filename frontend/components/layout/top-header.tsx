"use client";

import { LogOut, Menu } from "lucide-react";
import { useAuth } from "@/lib/auth/auth-context";

/**
 * Top header bar with user avatar (or initials fallback) and logout button.
 * Responsive: shows a menu icon on mobile for future sidebar toggle.
 */
export function TopHeader() {
  const { user, logout } = useAuth();

  const initials = user?.username
    ? user.username.slice(0, 2).toUpperCase()
    : "??";

  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4 sm:px-6">
      {/* Mobile menu button placeholder */}
      <button
        type="button"
        className="rounded-md p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 md:hidden"
        aria-label="Open navigation menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Spacer for desktop (sidebar handles branding) */}
      <div className="hidden md:block" />

      {/* User section */}
      <div className="flex items-center gap-3">
        {/* Avatar or initials fallback */}
        {user?.avatarUrl ? (
          <img
            src={user.avatarUrl}
            alt={`${user.username}'s avatar`}
            className="h-8 w-8 rounded-full object-cover"
          />
        ) : (
          <div
            className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-xs font-medium text-gray-700"
            aria-label={user?.username ? `${user.username}'s avatar` : "User avatar"}
          >
            {initials}
          </div>
        )}

        {/* Username (hidden on very small screens) */}
        {user?.username && (
          <span className="hidden text-sm font-medium text-gray-700 sm:inline">
            {user.username}
          </span>
        )}

        {/* Logout button */}
        <button
          type="button"
          onClick={() => void logout()}
          className="rounded-md p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
          aria-label="Log out"
        >
          <LogOut className="h-5 w-5" />
        </button>
      </div>
    </header>
  );
}
