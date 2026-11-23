import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async redirects() {
    // The overview is the landing page; temporary so the default can change later.
    return [{ source: "/", destination: "/overview", permanent: false }];
  },
};

export default nextConfig;
