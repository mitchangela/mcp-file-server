# Conversation summary: MCP file-server project

Written Oct 15, 2026. To continue in a new chat, paste this file and say: "Continue from this summary."

## 1. The project

Course: CS 3A / CS 3B elective, Week 6 (Model Context Protocol). Midterms Part 1, "Build your own."

Brief: build and deploy your own MCP file-server connector, then prove it by running a real
multi-step task across more than one agent session. The tool is meant to be kept for later
projects as shared memory for you and your agents.

Deliverables: working repository, README anyone can follow, tool-call transcript of the demo
task, documentation. Evidence also includes PLAN_LOG and CHECKPOINT files and a 5-minute live
demo at the Week 7 checkpoint. A short report covers stack, tool design choices and security
tradeoffs.

Minimum requirements:
1. Sandboxed workspace root. Every path resolved against it, escapes rejected.
2. At least 8 tools: file ops (list, read, write, str_replace, delete) plus git-lite or search.
3. Served over HTTPS through a tunnel and kept alive by a process manager.
4. Handoff protocol: PROJECT_STATE, PLAN_LOG, CHECKPOINTS, DECISIONS.
5. Connected to a real MCP client, tested on one multi-step task across 2+ sessions.
6. Short report on stack, tool design choices, security tradeoffs.

Stretch: if_version locking, search_code, a repo map, token auth.

Reference stack: Node.js + TypeScript SDK, Streamable HTTP, zod, ngrok static domain, pm2, git,
MCP Inspector then a real client. Alternatives (Python + FastMCP, pydantic, Cloudflare Tunnel,
systemd/Docker, stdio for local testing) score the same if justified in writing.

Milestones: M1 skeleton (`list_files` in Inspector), M2 sandbox + path tests, M3 deploy (tunnel,
process manager, real client connects), M4 protocol (handoff files, git-lite, bad-write guards),
M5 prove it (multi-agent run, report, demo).

## 2. Grading (100 points)

| Criterion | Pts |
|---|---|
| A. Agent efficiency (few purposeful calls, reads before writing, batching, small outputs, no blind retries) | 20 |
| B. Agent and tool management (roles, gated destructive tools, handoff across 2+ sessions, logged calls) | 20 |
| C. Tool design and implementation (8+ single-purpose tools, strict schemas, isError, Inspector + real client) | 20 |
| D. Tech stack and architecture (justified choices, clean separation, secrets in env vars, survives restart) | 15 |
| E. Security and sandboxing (traversal tests pass, endpoint needs a token, destructive actions gated/logged, threats noted) | 10 |
| F. Documentation, practice, demo (README reproducible, meaningful git history, smooth demo, Q&A) | 15 |

Bands: 90-100 Exemplary, 80-89 Proficient, 70-79 Developing, below 70 Revise and resubmit.
Efficiency is judged from the transcript and logs, not claims.

## 3. Your two files

1. The course PDF (project overview, sheets 16 to 20).
2. `mcp-handoff-and-asset-librarian.txt`: notes for a personal "freelance desk" MCP for your
   graphic design work (client brief tracker, invoice generator, asset librarian, plus a handoff
   feature to move a conversation between Claude accounts). Python with the official SDK preferred.

They are two different projects. Decision: the course project is the graded one. From your notes
only the handoff idea carries over (it became the four handoff files plus `read_state` and
`append_handoff`). The tracker, invoice generator and asset librarian are not graded and are
parked until after M5.

Conflicts and how they were resolved:
- Your notes assume a local desktop server and `~/mcp-handoffs/`. The course needs HTTPS via a
  tunnel and everything inside one `workspace/` root. Resolved: Streamable HTTP, handoffs inside workspace.
- Your notes have no auth. The course needs a token on the public endpoint. Resolved: bearer token + roles.
- The asset librarian reads design folders outside the sandbox. That would break the "nothing
  outside workspace/" rule. Resolved: skipped for now.

## 4. Decisions locked

| Layer | Pick |
|---|---|
| Language/SDK | Python + official MCP SDK (FastMCP), pinned `mcp>=1.9,<2` |
| Validation | pydantic |
| Transport | Streamable HTTP (stateless); stdio only for Inspector testing |
| Tunnel | ngrok, free static domain |
| Process manager | pm2 |
| Scope | Core only |

Why pinned below 2: `mcp` 2.x (2.3.0 at build time) renamed FastMCP to MCPServer and changed
other APIs. This code uses the 1.x API (tested on 1.30.0).

## 5. Pre-build checklist (10 steps) and your progress

1. Lock decisions: DONE
2. Accounts (GitHub: have it. ngrok: have it): DONE
3. Install tools (Python 3.11+, uv/pip, Node 20+, git, ngrok CLI, pm2): DONE
4. Repo skeleton: NEXT (you are starting this)
5. Handoff files
6. Tool design on paper
7. Security prep (token in `.env`)
8. Test list (traversal cases)
9. Pick the demo task
10. Timeline to the Week 7 checkpoint

Steps 4 to 9 are now covered by the code in this zip. See `docs/SETUP_GUIDE.md`.

## 6. Answers to your account questions

ngrok static domain: log in at dashboard.ngrok.com/domains. A free account gets one static dev
domain (looks like `abc123xyz.ngrok-free.dev`), usually assigned automatically. If none is
listed, click New + to reserve one. Then `ngrok config add-authtoken <token>` and
`ngrok http --url=<domain> <port>`.

Claude custom connectors: available on Free, Pro, Max, Team and Enterprise. Free plans are limited
to one custom connector (enough for this project). Check in Settings > Connectors for
"Add custom connector". Claude connects from Anthropic's cloud, not your device, so localhost
will not work and the ngrok URL is required.

Open question: not confirmed whether Claude's connector form lets you send a bearer token header.
The server supports both a header and a secret-path URL (`/s/<token>/mcp`). Test early.

## 7. What was built (this zip)

12 tools: `list_files`, `read_file`, `write_file`, `str_replace`, `delete_file`, `search_code`,
`git_status`, `git_diff`, `git_commit`, `git_log`, `read_state`, `append_handoff`.

- Sandbox: one `resolve()` for all paths. Rejects `..`, absolute paths, drive letters, `~`,
  encoded and backslash traversal, null bytes, `.git`, and symlinks leaving the root.
- Auth: bearer header or secret path. Three roles (reader / writer / admin), one token each.
  `/health` is open and returns only `{"status":"ok"}`.
- `if_version` locking (stretch): `read_file` returns a version; overwriting needs it.
- Delete gated: admin role, `confirm=true`, files only, handoff files protected.
- Audit log: `logs/tool_calls.jsonl` (time, role, tool, shortened args, ok/error, ms).
- Errors: `isError` with plain messages. Unexpected errors are logged on the server, not shown to the agent.
- Host-header allow list for the ngrok domain.
- Workspace is its own git repo, created on first start; handoff files seeded from `templates/`.
- Deploy: `ecosystem.config.js` (pm2 runs the server and the ngrok tunnel).

Tested at build time: 45 pytest tests pass. A live run over HTTP with a real MCP client passed
10/10 smoke checks (tool list, writes, overwrite refusal, path escape, delete gating, reader
token blocked from writing, wrong token rejected), plus the secret-path form, the allowed and
blocked Host header, and audit log lines.

Stdio mode (used by Inspector) also checked with a Python client: 12 tools, path escape returns
isError, `delete_file` marked destructive.

Not tested by Claude: the MCP Inspector app, ngrok, pm2, the Claude connector itself. Not built: repo map
(stretch).

## 8. What is left for you

- Set up (repo, venv, `.env`, tokens), run tests, run Inspector.
- Deploy with pm2 + ngrok, connect Claude, test restart and reboot persistence.
- Run the 3-session demo (`docs/DEMO_TASK.md`), save the transcript, export evidence.
- Write the report and fix up the README in your own words, add your own tests.
- Make meaningful git commits as you go. Commit the scaffold honestly as generated with Claude.
  Check your course's rules on AI-generated code, and be ready to explain every file in the Q&A.
- Practise the 5-minute demo.

## 9. Notes for the next Claude

- Call her "Cloud". She is Mitsu, a CS student in the Philippines who also does freelance design.
- Keep replies short, plain and punchy. Written work should not sound like AI.
- Do not rebuild the project. The code is done. Help her run, debug, deploy, and write docs.
