/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // Keep trailing slashes to match Django's URL patterns
  trailingSlash: true,
  async rewrites() {
    return [
      {
        // Proxy all /api/* requests to the Django backend
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*/",
      },
      {
        // Proxy social auth URLs to Django
        source: "/auth/:path*",
        destination: "http://localhost:8000/auth/:path*/",
      },
    ];
  },
};

export default nextConfig;
