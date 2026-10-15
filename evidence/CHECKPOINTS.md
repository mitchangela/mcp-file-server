# CHECKPOINTS

Append-only snapshots. One entry after each milestone or session: what was done,
what state the files are in, the last commit, what the next session should do.
Use append_handoff with kind CHECKPOINTS.

## 2026-10-15 11:41 UTC
Session checkpoint, start of M1. State: workspace holds only the template files (PROJECT_STATE, PLAN_LOG, CHECKPOINTS, DECISIONS) and an empty smoke/ folder. No server code, no commits yet. Goal is unchanged: a sandboxed MCP file server for AI agents. Next session: scaffold the server skeleton per the PLAN_LOG entry, then run the smoke test.

## 2026-10-15 11:47 UTC
Checkpoint, M1 guard tests. Done: ran the smoke test on smoke/test.txt. Create without if_version worked; overwrite without if_version, overwrite with a stale if_version, and delete without confirm were all refused with clear errors; delete with confirm=true succeeded (admin role confirmed). Files: smoke/ is back to just .gitkeep; the four handoff files are intact. Last commit: none yet. Not yet tested: path confinement, handoff-file delete protection, git tools. Next session: test those three, then commit and start M2.

## 2026-10-15 11:48 UTC
Checkpoint, M2 complete. Path confinement verified: `../` and absolute paths are both rejected. Server deployed with pm2 and ngrok; the connector works. `workspace/` has commits. Still open from M1: handoff-file delete protection test. Next: start the next milestone.

## 2026-10-15 11:50 UTC
Correction to the M2 checkpoint. The git repo is the workspace root, not a `workspace/` subfolder. It has one commit (`095e7ab`, "Add handoff files and project goal"). The four handoff files have uncommitted changes. Path confinement (`../` and absolute paths rejected), the pm2 + ngrok deploy and the working connector are as reported by the user. Next: commit the handoff files.

## 2026-10-15 11:56 UTC
Checkpoint, portfolio site steps 1-3. Files: site/index.html (header, hero, work grid with 4 cards, about, services, contact, footer) and site/style.css (tokens, responsive grid, hover states) written with placeholder content and gradient thumbnails. Not yet opened in a browser, so layout is untested. Steps 4-5 not started. Next session: swap in real work and name, check accessibility and mobile, then pick a host.

## 2026-10-15 11:59 UTC
Checkpoint, portfolio site responsive layout + README. Done: site/style.css gained phone (<=560px), tablet (561-860px) and reduced-motion rules plus larger nav tap targets; site/README.md written (files, preview, editing, breakpoints, status). index.html unchanged (already had the viewport meta). Not verified in a real browser, only by reading the CSS. Choices are in DECISIONS. Next session: check at 360/768/desktop widths, swap placeholders for real work and name, accessibility pass, then pick a host and publish.

## 2026-10-15 15:44 UTC
Checkpoint, session 3 (reader). Reviewed the work from sessions 1 and 2; the write attempt was refused. Fixed stale PROJECT_STATE lines so they match git_log: everything from sessions 1 and 2 is committed (HEAD bd0818b, working tree clean). No code or site files changed this session. Next session: unchanged from PROJECT_STATE (check portfolio site at 360/768/desktop widths, swap placeholders, accessibility pass, pick a host).
