"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type LucideIcon } from "lucide-react";

export interface NavItemProps {
  label: string;
  icon: LucideIcon;
  href: string;
}

export function NavItem({ label, icon: Icon, href }: NavItemProps) {
  const pathname = usePathname();
  const isActive =
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <Link
      href={href}
      className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
        isActive
          ? "bg-gray-100 text-gray-900"
          : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
      }`}
      aria-current={isActive ? "page" : undefined}
    >
      <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
      <span>{label}</span>
      {isActive && (
        <span
          className="ml-auto h-2 w-2 rounded-full bg-blue-600"
          aria-hidden="true"
        />
      )}
    </Link>
  );
}
