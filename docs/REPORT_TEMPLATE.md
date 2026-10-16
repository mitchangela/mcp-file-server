# Report: stack, tool design, security tradeoffs


## 1. Stack and why

| Layer | Choice | Why |
|---|---|---|
| Language and SDK | Python, official MCP SDK (FastMCP) | I know Python, and FastMCP builds tool schemas from type hints |
| Validation | pydantic limits on every tool input | Types and size limits are checked before any tool runs |
| Transport | Streamable HTTP | Claude connects from the cloud, so it needs a public HTTPS URL. The Inspector needed stdio mode instead, which I set with `-e MCP_TRANSPORT=stdio` after it first failed |
| Tunnel | ngrok, static domain | The URL stayed the same after `pm2 restart all`, so the connector kept working |
| Process manager | pm2 | Runs the server and the tunnel together and restarts them. On Windows I used `pm2-windows-startup` for reboot persistence |
| Version control | GitHub repo for the server code. Separate git repo at the workspace root for agent output | Agent commits stay apart from my code. The log shows agent commits like `a40117d` and `bd0818b` |
| Testing | pytest (71 passed, 2 skipped), MCP Inspector, smoke test (10/10) | The 2 skips are symlink tests, which can't run on Windows without admin rights |

Things I rejected, and why:
- **stdio only:** Claude's connector can't reach a local process. It needs a public HTTPS URL, so I used HTTP with ngrok. I kept stdio just for Inspector testing.
- **Header token only:** the Claude connector tried OAuth on the plain `/mcp` URL and failed, so I used the secret-path URL with "No sign-in". The tradeoff is in Section 4.

## 2. Tool design

20 tools, each doing one job. 12 are read-only, 6 are writer tools, and 2 are admin-only.

- **Small outputs:** `read_file` reads by line range (offset and limit), `search_code` and `git_diff` are capped (the diff at 200 lines), and `read_state` gives the project state and latest log in one call. In my demo, each new chat started with a single `read_state` and picked up from there.
- **Read before write:** replacing a file needs `if_version`. In my test, a file went from version `7281f9935640` to `1280b5c521a6` after an edit, and a write using the old version was rejected. This stops two agents from silently overwriting each other.
- **Precise edits:** `str_replace` changes one exact match, so the agent doesn't resend a whole file. In Session 2 it edited `style.css` with the version from its earlier read.
- **Plain errors:** failures come back as `isError` with a message that says what to do next, like "File already exists. Read it first and pass if_version, or use str_replace for a small edit." No stack traces.
- **Handoff tools:** `append_handoff` only adds to PLAN_LOG, CHECKPOINTS or DECISIONS, so an agent can't rewrite the history.
- **Freelance desk tools:** the instructor asked for a feature that helps with my own niche, so I added dated handoff notes (`save_handoff`, `load_handoff`, `list_handoffs`) and an asset librarian (`reindex`, `search_assets`, `list_recent`, `find_by_client`, `tag_asset`). The librarian only reads my design folders. It writes its index to a separate SQLite file, and `reindex` is admin-only because it scans the disk.

## 3. Agent and tool management

- **Three roles, one token each:** reader, writer and admin. The server checks the role on every call. In my demo, the reader token could read the project but was refused when it tried to write: "Tool 'append_handoff' needs the 'writer' role; this connection has 'reader'."
- **Delete is gated three ways:** it needs the admin role, it needs `confirm=true`, and the four handoff files can't be deleted (this last one is from the tool description, and I didn't test deleting a handoff file). Without confirm, my delete was refused, and with `confirm=true` it went through.
- **Every call is logged:** time, role, tool, shortened arguments, result, and duration. Long file contents are cut down, so the log stays small and doesn't hold file text. My demo run is 35 calls. The full log had 83 calls at the time of the demo and has 96 now, after the 13 calls for the 8 freelance desk tools.
- **Handoff across sessions:** PROJECT_STATE, PLAN_LOG, CHECKPOINTS and DECISIONS let a fresh chat pick up with no context. Session 2 started with one `read_state` call and finished the work without asking what the project was. Session 3 (reader) reviewed it and caught a stale line in PROJECT_STATE, which I fixed afterward.
- **A second layer on the client side:** Claude's connector settings ask for approval before each tool call, so a person can still stop a call that the server would allow.

## 4. Security and tradeoffs

| Threat | What I did | What is left |
|---|---|---|
| Path traversal (`..`, absolute, encoded, backslash, null byte) | One `resolve()` for every path, tested | In Inspector, `../../etc/passwd` and `/etc/passwd` were both refused. pytest covers the rest, and I added `..%2F`, a network path and a valid name with two dots |
| Symlink pointing outside | `resolve()` follows links, then checks the root | The two symlink tests were skipped on my Windows machine, so I didn't see them run |
| Asset tools reading too much of my disk | Only folders listed in `ASSET_ROOTS` are scanned; my home folder is refused (a drive root is refused in the code too) | `test_refuses_home_folder` in tests/test_assets.py |
| Tampering with git hooks/config | `.git` blocked in file tools; git runs without a shell | pytest rejects `.git/config` and `.git/hooks` paths |
| Open public endpoint | Token required on every request except `/health` | Smoke test passed 10/10. Tokens are long-lived, and rotating means editing `.env`. I rotated mine during setup |
| Token in URL (secret-path mode) | Used only because Claude's connector tried OAuth on the plain `/mcp` URL and failed | The URL can appear in ngrok logs and browser history, and anyone with it has that role. I hid it in screenshots. A header token is safer |
| Wrong role doing damage | Roles per token | Roles belong to tokens, not agents. I used the admin token for my testing |
| Accidental or bad delete | Gated, logged, handoff files protected | Deleted files are gone, though committed ones can be restored from git |
| Huge writes or reads | Size and line caps | No rate limiting |
| Prompt injection from file contents | Small tool set, no shell, roles | An agent can still be fooled by text in a file. Not fully solved |
| DNS rebinding / wrong Host | Allowed host list | It depends on `PUBLIC_HOST` being right in `.env` |

**What I would add next:** rate limiting, OAuth so no token has to sit in the URL, and a separate identity for each agent so the log shows which agent did what.

## 5. What I learned

Most of my problems weren't in the code. They were setup problems, like a nested folder, a server running in the wrong mode for Inspector, and Claude's connector trying OAuth on a URL that used a token. The version check taught me the most: it stopped a stale write from wiping out an edit, and the agent had to re-read and try again. Handoff files worked better than I expected, because a brand new chat picked up the project from one `read_state` call. The reviewer chat also caught a stale line in PROJECT_STATE that said my work wasn't committed when it was, so those files can drift out of date, and I had to fix it by hand. If I did it again, I'd set up the secret-path URL from the start and add per-agent identities.
