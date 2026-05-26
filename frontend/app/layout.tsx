import type { Metadata } from "next";
import { QueryProvider } from "@/lib/providers/query-provider";
import { AuthContextProvider } from "@/lib/auth/auth-context";
import { Toaster } from "@/components/ui/toaster";
import "./globals.css";

export const metadata: Metadata = {
  title: "Explorer - DevConn",
  description: "AI Codebase Explorer",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <AuthContextProvider>{children}</AuthContextProvider>
        </QueryProvider>
        <Toaster />
      </body>
    </html>
  );
}
