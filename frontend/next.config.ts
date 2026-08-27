import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const nextConfig: NextConfig = {
  agentRules: false,
  // Emits .next/standalone with only the traced runtime dependencies, so the Docker
  // runner stage does not have to ship the full node_modules tree.
  output: "standalone",
};
const withNextIntl = createNextIntlPlugin("./lib/i18n/request.ts");

export default withNextIntl(nextConfig);
