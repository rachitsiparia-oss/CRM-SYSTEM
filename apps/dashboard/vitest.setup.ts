import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Without `test.globals: true` in vitest.config.ts, @testing-library/react's
// automatic per-test DOM cleanup does not self-register — without this,
// component tests across files (or across `it` blocks) leak DOM nodes into
// each other, since jsdom's `document` persists between tests.
afterEach(() => {
  cleanup();
});
