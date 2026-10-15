# PROJECT_STATE

Single source of truth for the project. Keep it short. Update it with str_replace
at the end of every work chunk. A new session reads this first.

## Goal
Goal: Build and deploy an MCP file server that lets AI agents safely read and write files in a sandboxed workspace.

## Current milestone
M2 done: path confinement verified, server deployed. Moving on.

## What works
- Write/delete guards (if_version, confirm=true).
- Path confinement: `../` and absolute paths rejected.
- Deployed with pm2 + ngrok; the connector works.
- Repo is at the workspace root. Everything from sessions 1 and 2 is committed (HEAD `bd0818b`, 4 commits; working tree clean per git_status).

## What is broken
-

## Side task: designer portfolio site (site/)
Steps 1-3 done earlier (HTML, CSS, sample content with placeholder name Mara Reyes and gradient thumbnails). Session 2: responsive layout (phone/tablet/desktop tiers, reduced-motion, tap targets) and short site/README.md done. Still untested in a real browser. Real images, final name/email, accessibility audit and publishing not started.

## Next step
Portfolio site: open in a browser at ~360px, ~768px and desktop widths to confirm layout; swap in real work and name; accessibility pass; pick a host and publish.

## Open questions
-
