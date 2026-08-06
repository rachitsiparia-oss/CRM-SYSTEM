# Phase 16 — Frontend Performance Report

Generated: 2026-08-02. Evidence-based — every claim cites the file(s) read.

## Bundle splitting / lazy loading

### Found and fixed: chart components eagerly bundled the full ECharts library

- **Found**: `apps/dashboard/src/components/charts/{bar,line,pie}-chart.tsx` each imported
  `echarts-for-react` (which wraps the full `echarts` package — a large dependency) directly at
  the top of the file. Any route importing one of these components would include ECharts in that
  route's initial JS bundle even before the chart itself needed to render — CLAUDE.md §5.1's
  "avoid importing large libraries into shared client bundles when smaller or server-side
  alternatives exist" applies directly. `area-chart.tsx` is a thin wrapper around `line-chart.tsx`
  and inherits whatever `line-chart.tsx` does.
- **Fix**: split each chart component into a thin wrapper (kept at the original filename/public
  API — no caller needs to change) and a `*-impl.tsx` file holding the actual `echarts-for-react`
  usage. The wrapper uses `next/dynamic` (`ssr: false`, since charts are canvas-based and
  client-only regardless) to defer fetching the impl chunk — and therefore the ECharts bundle —
  until the component actually needs to render a real chart. The existing `loading` prop (already
  used everywhere a chart is rendered, to show `ChartSkeleton` while data is fetching) is checked
  *before* the dynamic import is even triggered, so the loading-skeleton case never fetches the
  chart chunk at all, only the eventual real-render case does.
- **Verified**: `tsc --noEmit` (clean), `eslint` on `src/components/charts/` (clean), and a full
  `pnpm run build` (succeeded, confirming Next.js/webpack resolves the dynamic imports and the
  app still builds every route).

## Image optimization

**Reviewed, already correct**: grepped for raw `<img>` tags anywhere in `apps/dashboard/src` —
none found. Every image-rendering call site (`product-images.tsx`, `image-upload.tsx`) already
uses `next/image`, which provides automatic responsive sizing, lazy loading below the fold, and
format optimization by default. No change needed.

## Virtualization

**Reviewed — no client-rendered unbounded list found that virtualization alone would fix.**
Every list/table view checked (`DataTable`, `data-table-pagination.tsx`) is server-paginated with
a bounded page size (CLAUDE.md §5.1's preferred pattern: "Use server-side pagination... instead
of" client-side virtualization of a fully-fetched dataset) — there is nothing unbounded rendered
in the DOM at once in those views, so `TanStack Virtual` genuinely isn't needed there yet.

One real exception found: `apps/dashboard/src/app/(app)/communications/inbox/
conversation-timeline.tsx`'s `useConversationTimeline` hook
(`apps/dashboard/src/lib/hooks/use-communications.ts`) calls
`GET /conversations/{id}/timeline` with no pagination parameters at all, and the component
`.map()`s over every returned entry unconditionally — this is the "message histories" case
CLAUDE.md §5.1 names explicitly as needing cursor pagination and/or virtualization. **Not fixed
in this pass**: the real fix is a backend contract change (add cursor pagination to the timeline
endpoint, `app/communications/router.py`), which is a cross-stack change beyond this task's
frontend-only scope, and virtualizing the render alone without fixing the unbounded fetch would
address only half the problem — the network payload would stay unbounded even if the DOM cost
didn't. In practice, a single customer conversation's realistic message volume (dozens to low
hundreds of messages) makes this a real but not urgent gap; recorded here rather than silently
passed over, so whoever picks up communications-hub work next has this already scoped:
paginate `GET /conversations/{id}/timeline` on the backend, switch the frontend hook to
`useInfiniteQuery`, and add `useVirtualizer` to the render if message counts turn out to warrant
it in practice.

## Outcome

- Real fix: chart bundle code-splitting (3 components), verified via typecheck/lint/build.
- Reviewed, already correct: image optimization.
- Reviewed, documented as a scoped cross-stack recommendation rather than force-fixed:
  conversation timeline pagination/virtualization.
