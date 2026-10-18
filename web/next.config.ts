import type { NextConfig } from "next";

const onGitHubPages = process.env.GITHUB_PAGES === "true";

const nextConfig: NextConfig = {
  ...(onGitHubPages ? { output: "export" as const, basePath: "/SOPia" } : {}),
  images: { unoptimized: onGitHubPages },
};

export default nextConfig;
