import {defineConfig, globalIgnores} from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  // CommonJS files (the test alias hook) can only load modules with require().
  {files: ["**/*.cjs"], rules: {"@typescript-eslint/no-require-imports": "off"}},
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    ".test-build/**",
    "node_modules/**",
    "next-env.d.ts"
  ])
]);