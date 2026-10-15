# DECISIONS

Append-only. Each entry: the choice, the reason, and what was rejected.
Use append_handoff with kind DECISIONS.

## 2026-10-15 11:41 UTC
Decision: build in milestone order and start with path sandboxing before any write tool. Reason: the goal is safe file access for agents, so a write tool without root confinement would defeat the point and be costly to retrofit. Rejected: adding write_file first and hardening later (risks unsafe code landing in early commits); skipping the smoke test (nothing else proves the server works end to end).

## 2026-10-15 11:47 UTC
Decision: rely on the server's version check (if_version) and confirm flag as the standard write and delete workflow: read first to get the version, then str_replace for small edits or write_file with if_version for full rewrites, and delete only with confirm=true. Reason: the smoke test showed these guards refuse blind, stale and unconfirmed changes, which is what makes agent writes safe in a shared workspace. Rejected: adding our own wrapper checks on top (duplicates what the server already enforces and adds code to maintain); bypassing the guards in tests (would hide whether they work).

## 2026-10-15 11:58 UTC
Decision: treat "steps 4 and 5" as the user's narrowed scope for this session: step 4 = responsive layout only, step 5 = short site/README.md. The original PLAN_LOG meaning (4 = real images and a11y polish, 5 = publish) is deferred, not dropped. Reason: the user said so directly. Rejected: doing the original steps anyway (no real images or host chosen yet).
Decision: keep CSS-only responsiveness with three tiers (phone up to 560px: one column, full-width buttons, wrapping nav; 561-860px: two-column grid; wider: existing auto-fill grid). Reason: the existing grid already adapts, so small additions beat a rewrite; no JS needed. Rejected: hamburger menu (4 links fit on a wrapped row, needs JS); a CSS framework.
Decision: added prefers-reduced-motion and 10px vertical padding on nav links for tap targets. Reason: cheap accessibility wins that touch only layout. Rejected: a full accessibility audit now (out of scope this session).
Decision: README documents the placeholder name/email and how to swap in real images. Reason: those are the first things the next session must change. Rejected: a long README.
