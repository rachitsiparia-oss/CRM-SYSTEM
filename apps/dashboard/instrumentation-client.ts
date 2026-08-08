import * as Sentry from "@sentry/nextjs";

// Optional: only initializes when a real DSN is configured, matching the
// same "disabled without crashing" contract apps/api and apps/worker use
// (CLAUDE.md section 21). NEXT_PUBLIC_* is required here since this file
// runs in the browser bundle.
const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? process.env.NODE_ENV,
    sendDefaultPii: false,
    tracesSampleRate: 0.1,
  });
}

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
