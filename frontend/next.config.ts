import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const nextConfig: NextConfig = {
  agentRules: false,
  // The dev server refuses /_next/* requests from an origin it does not recognise.
  // 127.0.0.1 is not allowed by default, so opening the app there served the HTML
  // but 403'd every chunk: the page rendered, React never hydrated, and nothing
  // was interactive. Production (next start) has no such check, which is why it
  // only bit in dev. Both loopback spellings are listed because the README, the
  // backend CORS_ORIGINS and the verification scripts all use 127.0.0.1.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  // Emits .next/standalone with only the traced runtime dependencies, so the Docker
  // runner stage does not have to ship the full node_modules tree.
  output: "standalone",
};
const withNextIntl = createNextIntlPlugin("./lib/i18n/request.ts");

export default withNextIntl(nextConfig);
