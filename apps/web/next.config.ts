import type { NextConfig } from "next";
import path from "path";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
// Monorepo root — required so Turbopack can resolve packages/shared/types.
const monorepoRoot = path.resolve(process.cwd(), "../..");

const nextConfig: NextConfig = {
  turbopack: {
    root: monorepoRoot,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_URL}/api/:path*`,
      },
      {
        source: "/storage/:path*",
        destination: `${API_URL}/storage/:path*`,
      },
    ];
  },
};

export default nextConfig;
