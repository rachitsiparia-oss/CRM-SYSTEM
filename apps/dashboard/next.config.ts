import { withSentryConfig } from "@sentry/nextjs";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
};

export default withSentryConfig(nextConfig, {
  org: "aevum-5f",
  project: "rkpr-crm-dashboard",
  // Source-map upload needs an org-scoped auth token (SENTRY_AUTH_TOKEN) in
  // the build environment; silently skips uploading (not the build) without
  // one — CLAUDE.md section 21's "optional integrations stay disabled
  // without crashing unrelated modules" applied to the build step.
  silent: true,
  widenClientFileUpload: true,
});
