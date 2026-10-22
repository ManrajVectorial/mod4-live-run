import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output: a self-contained server bundle for deployment.
  output: "standalone",
  poweredByHeader: false,
  // Image optimisation needs sharp, whose native library is LGPL (AGENTS.md rule 7).
  // sharp is replaced by an empty stand-in (package.json overrides) and never loaded.
  images: { unoptimized: true },
};

export default nextConfig;
