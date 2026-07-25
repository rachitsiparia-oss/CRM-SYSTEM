// Non-secret shared configuration, feature flags, and environment type
// definitions — ARCHITECTURE_AND_TECH_STACK.md section 5.7. Secrets must
// never be committed here.

export const API_VERSION_PREFIX = "/api/v1" as const;

export const RESTAURANT_TIMEZONE = "Asia/Kolkata" as const;
export const DEFAULT_CURRENCY_CODE = "INR" as const;
