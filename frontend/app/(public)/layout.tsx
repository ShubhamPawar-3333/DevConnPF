export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Minimal branding header */}
      <header className="border-b border-gray-200 bg-white px-6 py-4">
        <span className="text-lg font-semibold text-gray-900">DevConn</span>
      </header>

      {/* Public content area */}
      <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
    </div>
  );
}
