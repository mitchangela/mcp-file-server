# Report: stack, tool design, security tradeoffs

Short. Aim for 2 pages. The starter text below is true for this build, but rewrite it in your
own words and add what you actually saw while testing.

## 1. Stack and why

| Layer | Choice | Why (edit) |
|---|---|---|
| Language and SDK | Python, official MCP SDK (FastMCP) | I already know Python; FastMCP turns type hints into tool schemas |
| Validation | pydantic `Field` limits on every tool input | Strict schemas: types, length limits, enums |
| Transport | Streamable HTTP, stateless | Claude connects from the cloud, so it must be HTTPS. Stateless means a restart loses nothing |
| Tunnel | ngrok with a static domain | Same URL after restarts, free |
| Process manager | pm2 | Restarts crashed processes, runs on any OS |
| Version control | git in the repo, plus a separate git repo inside `workspace/` | Server code and agent output stay apart |
| Testing | pytest, MCP Inspector, smoke test with a real client | |

Things I rejected, and why: (write 2 or 3, for example TypeScript, stdio only, Docker)

## 2. Tool design

12 tools, each doing one thing. Reads are split from writes so roles can be scoped.

- Small outputs: `read_file` pages by line, `search_code` is capped, `git_diff` is capped, `read_state` gives the handoff in one call
- Read before write: overwriting needs `if_version`, so two agents cannot silently overwrite each other
- `str_replace` needs exactly one match, so edits are precise and cheap
- Errors use `isError` with a plain message that says what to do next
- (add your own points, with a real example from your transcript)

## 3. Agent and tool management

- Three roles (reader, writer, admin), one token each
- Destructive tool gated three ways: admin role, `confirm=true`, handoff files protected
- Every call logged with time, role, tool, shortened arguments, result, duration
- Handoff through PROJECT_STATE, PLAN_LOG, CHECKPOINTS, DECISIONS across 3 sessions

## 4. Security and tradeoffs

| Threat | What I did | What is left |
|---|---|---|
| Path traversal (`..`, absolute, encoded, backslash, null byte) | One `resolve()` for every path, tested | |
| Symlink pointing outside | `resolve()` follows links, then checks the root | |
| Tampering with git hooks/config | `.git` blocked in file tools; git runs without a shell | |
| Open public endpoint | Token required on every request except `/health` | Tokens are long-lived; rotate by editing `.env` |
| Token in URL (secret-path mode) | Used only because the client form may not send headers | URL can appear in ngrok logs and browser history. Header mode is safer |
| Wrong role doing damage | Roles per token | Roles belong to tokens, not to individual agents |
| Accidental or bad delete | Gated, logged, handoff files protected | Deleted files are gone. The workspace git repo can restore committed ones |
| Huge writes or reads | Size and line caps | No rate limiting |
| Prompt injection from file contents | Small tool set, no shell, roles | An agent can still be fooled by text in a file. Not fully solved |
| DNS rebinding / wrong Host | Allowed host list | |

Write your own conclusion: what you would add next (rate limiting, OAuth, per-agent identity).

## 5. What I learned

(3 to 5 plain sentences)
