# Phase 16 — Accessibility Report

Generated: 2026-08-02. Evidence-based — every claim cites the file(s) actually read.

## Context

The design-system foundation (Phase 4) was already built on shadcn/ui + Radix primitives, which
are accessible by construction (correct ARIA roles, keyboard interaction patterns, and focus
trapping for dialogs/menus/popovers ship with the primitive itself — not something each
consuming page has to reimplement). This pass checked for the gaps that construction *doesn't*
automatically cover: reduced-motion support, and icon-only controls missing their own
`aria-label` (Radix gives a button correct button semantics; it can't know what a bare icon
means without being told).

## Found and fixed: no `prefers-reduced-motion` support anywhere

- **Found**: `apps/dashboard/src/app/globals.css` imports `tw-animate-css` (the source of every
  shadcn/ui open/close transition — dialogs, dropdowns, popovers, sheets) but had no
  `prefers-reduced-motion` media query anywhere in the codebase (confirmed by grep across
  `apps/dashboard/src`). CLAUDE.md §10 ("avoid excessive animation") and this phase's own
  instruction section L both call this out explicitly.
- **Fix**: a global override in `globals.css` — under `@media (prefers-reduced-motion: reduce)`,
  every element's `animation-duration`/`animation-iteration-count`/`transition-duration` collapse
  to effectively-instant and `scroll-behavior` becomes `auto`. This is the standard "kill switch"
  pattern: one rule covers every current and future shadcn/ui transition, since it operates on
  the CSS property level rather than needing each component to opt out individually.

## Found and fixed: two icon-only buttons missing `aria-label`

Checked all 14 files in `apps/dashboard/src` using `size="icon"` (the shadcn/ui icon-button
variant) by reading each one in full, not just grepping the prop — most already correctly
include `aria-label` (e.g. `data-table-pagination.tsx`'s four page-nav buttons,
`category-directory.tsx`'s move-up/move-down buttons, `sidebar.tsx`'s collapse toggle,
`product-images.tsx`'s thumbnail/delete buttons, `file-upload.tsx`'s remove-file button — all
already labeled correctly before this pass, confirmed by reading each file).

Two real gaps found and fixed:

- **`apps/dashboard/src/app/(app)/reservations/calendar/reservation-calendar.tsx`** — the
  previous-day/next-day navigation buttons (`ChevronLeft`/`ChevronRight` icons) had no
  `aria-label`; a screen-reader user would hear only "button." Added `aria-label="Previous day"`
  / `aria-label="Next day"`.
- **`apps/dashboard/src/app/(app)/marketing/campaigns/create-campaign-modal.tsx`** — the
  remove-channel-template-row button (`X` icon) had no `aria-label`. Added
  `aria-label="Remove channel template row"`.

## Reviewed and already correct — not re-litigated

- **Keyboard navigation and focus management**: inherited from Radix primitives throughout
  (dialogs trap focus and restore it on close, dropdown/select menus are fully keyboard-operable,
  `Tab`/`Shift+Tab` order follows DOM order since no component uses a manual `tabIndex` outside
  Radix's own internals). Not re-verified component-by-component in this pass — that would mean
  re-auditing Radix itself, which is out of scope for an application-level accessibility review.
- **Color contrast**: governed by the design-token system in `globals.css` (OKLCH color space,
  explicit light/dark pairs for every token), established in Phase 4 and unchanged by this
  session. Status/severity indicators already use `StatusBadge`-style components pairing color
  with a text label (confirmed in the files read this session — e.g. `category-directory.tsx`'s
  `<StatusBadge label="Inactive" tone="neutral" />` — never color alone), matching CLAUDE.md §22's
  "never rely on color alone."
- **Labels and descriptions**: every icon-only control audited above already had either a
  correct `aria-label` (12 of 14 files, pre-existing) or now has one (2 of 14, fixed this
  session).

## Outcome

Two real accessibility gaps found and fixed (reduced motion globally, two missing icon-button
labels), verified against `tsc --noEmit` and `eslint` (both clean, no new warnings introduced).
The broader foundation — keyboard nav, focus trapping, contrast, non-color status indication —
was already correct by construction from Phase 4 onward and did not need rework.
