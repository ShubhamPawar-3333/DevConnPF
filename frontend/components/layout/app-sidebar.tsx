"use client";

import {
  LayoutDashboard,
  GitBranch,
  Search,
  Settings,
  FolderPlus,
  Share2,
  BarChart3,
  User,
  type LucideIcon,
} from "lucide-react";
import { NavItem } from "./nav-item";

export interface NavEntry {
  label: string;
  icon: LucideIcon;
  href: string;
}

/**
 * Declarative navigation configuration.
 * To add a new module to the super-app, add an entry here and create
 * the corresponding route group directory. No other changes needed.
 */
export const navConfig: NavEntry[] = [
  { label: "Dashboard", icon: LayoutDashboard, href: "/dashboard" },
  { label: "Repositories", icon: GitBranch, href: "/repos" },
  { label: "New Repository", icon: FolderPlus, href: "/repos/new" },
  { label: "Search", icon: Search, href: "/search" },
  { label: "Sharing", icon: Share2, href: "/sharing" },
  { label: "Analytics", icon: BarChart3, href: "/analytics" },
  { label: "Profile", icon: User, href: "/profile/edit" },
  { label: "Settings", icon: Settings, href: "/settings" },
];

export function AppSidebar() {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-gray-200 bg-white md:flex">
      {/* Brand header */}
      <div className="flex h-16 items-center border-b border-gray-200 px-6">
        <span className="text-lg font-semibold text-gray-900">DevConn</span>
      </div>

      {/* Scrollable navigation area — supports 8+ entries without overflow */}
      <nav
        className="flex-1 overflow-y-auto p-4"
        aria-label="Main navigation"
      >
        <ul className="flex flex-col gap-1" role="list">
          {navConfig.map((entry) => (
            <li key={entry.href}>
              <NavItem
                label={entry.label}
                icon={entry.icon}
                href={entry.href}
              />
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}
