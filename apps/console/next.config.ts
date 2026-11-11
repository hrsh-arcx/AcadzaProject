import type { NextConfig } from "next";
import { loadEnvConfig } from "@next/env";
import path from "node:path";
// npm workspaces run Next from apps/console; local secrets live at repo root.
// Deployment environment variables take precedence over root .env values.
loadEnvConfig(path.resolve(process.cwd(), "../.."), undefined, undefined, true);
const config: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "same-origin" },
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
    ];
  },
};
export default config;
