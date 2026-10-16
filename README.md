# MCP File Server

A sandboxed file server for AI agents, built with the official Python MCP SDK (FastMCP).
Agents read, edit, search and commit files inside one `workspace/` folder, and hand work
to each other through four shared files: PROJECT_STATE, PLAN_LOG, CHECKPOINTS, DECISIONS.

> DRAFT: check every command on your own machine and rewrite parts in your own words
> before you submit. A classmate should be able to follow this from scratch.

## What you need

- Python 3.11+
- Node 20+ (for MCP Inspector and pm2)
- git
- ngrok account, CLI installed and authtoken added, one free static domain
- pm2: `npm install -g pm2`

## Setup

```bash
git clone <your-repo-url> mcp-file-server
cd mcp-file-server
python -m venv .venv
# macOS/Linux:  source .venv/bin/activate
# Windows:      .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env          # Windows: copy .env.example .env
python scripts/gen_token.py   # run once per token, paste into .env
```

Edit `.env`: set `MCP_TOKEN_ADMIN` (and optionally `_WRITER`, `_READER`) and `PUBLIC_HOST`
(your ngrok domain, no `https://`).

## Run the tests

```bash
pytest -q
```

## Run locally

```bash
python server.py                      # http://127.0.0.1:8000/mcp
python scripts/smoke_test.py http://127.0.0.1:8000/mcp <admin-token> <reader-token>
```

MCP Inspector (stdio mode, no tokens needed):

```bash
# macOS/Linux
MCP_TRANSPORT=stdio npx @modelcontextprotocol/inspector .venv/bin/python server.py
# Windows PowerShell
$env:MCP_TRANSPORT="stdio"; npx @modelcontextprotocol/inspector .venv\Scripts\python.exe server.py
```

## Deploy (tunnel + process manager)

```bash
pm2 start ecosystem.config.js    # starts the server and the ngrok tunnel
pm2 status
pm2 save
pm2 startup                      # Linux/macOS: run the command it prints
curl https://<your-domain>/health
python scripts/smoke_test.py https://<your-domain>/mcp <admin-token> <reader-token>
```

## Connect a client

Claude: Settings > Connectors > Add custom connector, then paste the URL.

- Clients that can send headers: `https://<your-domain>/mcp` with `Authorization: Bearer <token>`.
- Claude's connector form may not let you set a header. Use the secret-path form instead:
  `https://<your-domain>/s/<token>/mcp`. The token is then part of the URL, so treat the URL as a secret.

## Tools

| Tool | Role needed | What it does |
|---|---|---|
| `list_files` | reader | List one directory |
| `read_file` | reader | Read lines `offset`..`offset+limit`, returns a version |
| `search_code` | reader | Find text or regex across files, capped results |
| `git_status` | reader | Branch and changed files |
| `git_diff` | reader | Line changes, capped at 200 lines |
| `git_log` | reader | Recent commits |
| `read_state` | reader | PROJECT_STATE plus latest log entries, one call |
| `write_file` | writer | Create a file; replacing needs `if_version` |
| `str_replace` | writer | Replace one exact match; optional `if_version` |
| `git_commit` | writer | Stage and commit |
| `append_handoff` | writer | Append to PLAN_LOG, CHECKPOINTS or DECISIONS |
| `delete_file` | admin | Delete one file, needs `confirm=true` |
| `save_handoff` | writer | Save a dated handoff note (`title`, `content` up to 8000 chars) in `workspace/handoffs/` |
| `load_handoff` | reader | Load the newest handoff note matching a title |
| `list_handoffs` | reader | List recent handoff notes |
| `reindex` | admin | Scan the `ASSET_ROOTS` design folders and update the SQLite asset index |
| `search_assets` | reader | Search indexed files by name, tag or client; month/year words filter by modified date |
| `list_recent` | reader | Newest indexed files, optionally by file type |
| `find_by_client` | reader | All indexed files tagged with a client name |
| `tag_asset` | writer | Add tags and a client to a file or folder in the index |

Errors come back with `isError` and a plain message. No stack traces reach the agent.

## Freelance desk tools

Two extra tool groups for my freelance design work.

- **Handoff notes:** `save_handoff`, `load_handoff` and `list_handoffs` store dated notes
  (`YYYY-MM-DD_title.txt`) in `workspace/handoffs/`, so a new chat can pick up where the last one stopped.
- **Asset librarian:** `reindex`, `search_assets`, `list_recent`, `find_by_client` and `tag_asset`
  keep a SQLite index of my design files. It is read-only on the design folders, skips junk
  folders, and only re-indexes changed files. Set `ASSET_ROOTS` in `.env` to full folder paths
  separated by `;`. A drive root or home folder is refused.

## Handoff protocol

Every session starts with `read_state`. Before work: write the plan to PLAN_LOG. After work:
update PROJECT_STATE, add a CHECKPOINT, log any DECISION, commit. The next session picks up
from those files and nothing else. See `docs/DEMO_TASK.md`.

## Security summary

- Every path is resolved against the workspace root. `..`, absolute paths, encoded and
  backslash tricks, null bytes, `.git` and symlinks that leave the root are rejected.
- The public endpoint needs a token. Three roles limit what each token can do.
- Destructive action is gated: admin role, `confirm=true`, handoff files protected.
- Every tool call is logged to `logs/tool_calls.jsonl` (long arguments shortened).
- Only the Host names you list are accepted (DNS rebinding protection).

## Project layout

```
server.py          entry point, wires tools and auth
config.py          settings from environment variables
sandbox.py         path resolving and escape checks
auth.py            bearer token / secret path, roles
audit.py           role check, audit log, error handling for every tool
tools/             files.py, search.py, git_tools.py, handoff.py, handoff_notes.py, assets.py
tests/             sandbox and tool tests
templates/         starting copies of the four handoff files
workspace/         the agents' sandbox (own git repo, created on first start)
data/              assets.db, the local asset index (git-ignored)
scripts/           gen_token, smoke_test, export_evidence
docs/              summary, setup guide, report and transcript templates
evidence/          exported handoff files and logs for submission
```
