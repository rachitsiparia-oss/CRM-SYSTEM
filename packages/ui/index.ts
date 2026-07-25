// Shared design-system primitives — ARCHITECTURE_AND_TECH_STACK.md
// section 5.4.
//
// shadcn/ui components are locally owned per shadcn convention; the
// dashboard app currently owns its own components under
// apps/dashboard/src/components/ui. Components move into this package only
// once a second app genuinely needs to share them — see CLAUDE.md's rule
// against overabstracting one-off UI.

export {};
