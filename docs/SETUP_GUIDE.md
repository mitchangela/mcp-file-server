# Setup guide: what's left for you

You finished checklist steps 1 to 3 (decisions, accounts, installs). The code scaffold is
in this folder. Work through these in order. Tick each box when it is done.

## Step 4. Repo skeleton

- [/] Unzip, open the folder in your editor
- [/] `git init`, then make the first commit. Say honestly what it is, for example:
      `Add initial scaffold generated with Claude`
- [/] Create the GitHub repo and push: `git remote add origin <url>`, `git push -u origin main`
- [/] Create the venv and install: `python -m venv .venv`, activate it, `pip install -r requirements-dev.txt`
- [/] Read through every file in `sandbox.py`, `audit.py`, `auth.py` and `tools/`. You will be asked
      about them in the Q&A, so you need to be able to explain each one.

From here on, commit your own work in small steps with clear messages (testing, config
changes, fixes, docs). The rubric reads your git history.

## Step 5. Handoff files

- [/] They are copied from `templates/` into `workspace/` the first time the server starts
- [/] Open `workspace/PROJECT_STATE.md` and fill in the goal

## Step 6. Tool design

- [/] Read the tool table in `README.md`. Be ready to say why each tool is single-purpose
- [/] Be ready to explain why `write_file` needs `if_version` to overwrite

## Step 7. Security prep

- [/] `python scripts/gen_token.py` (run it once per token)
- [/] `cp .env.example .env`, paste tokens, set `PUBLIC_HOST` to your ngrok domain
- [/] Check `.env` is not tracked: `git status` should not list it

## Step 8. Tests

- [/] `pytest -q` should show all tests passing (45 when this was built)
- [/] Add at least one traversal case of your own to `tests/test_sandbox.py`

## M1. Skeleton in MCP Inspector

- [/] Run Inspector (command in README, stdio mode)
- [/] Open Tools, run `list_files`, then `read_state`
- [/] Screenshot it for your report

## M2. Sandbox

- [/] In Inspector, call `read_file` with `../../etc/passwd` and `/etc/passwd`. Both must return an error
- [/] Screenshot the errors and the passing pytest run

## M3. Deploy

- [/] `pm2 start ecosystem.config.js` then `pm2 status` (both apps online)
- [/] `curl https://<domain>/health` returns `{"status":"ok"}`
- [/] `python scripts/smoke_test.py https://<domain>/mcp <admin> <reader>`: all checks pass
- [/] Add the custom connector in Claude (README, "Connect a client"). Free plan allows one connector
- [/] If Claude's form has no header field, use the secret-path URL and note the tradeoff in your report
- [/] Restart test: `pm2 restart all`, then check the connector still works
- [/] Reboot persistence: `pm2 save` and `pm2 startup` (Linux/macOS). On Windows use a startup
      task or the `pm2-windows-startup` package, and say which you used

## M4. Protocol

- [/] Run a short session that touches all four handoff files
- [/] Try a bad write on purpose (overwrite without version, stale version, delete without confirm)
      and keep the error messages for the report

## M5. Prove it

- [/] Run the demo task in `docs/DEMO_TASK.md` across 2 or more sessions
- [ ] Save the chat transcript, fill `docs/TRANSCRIPT_TEMPLATE.md`
- [/] `python scripts/export_evidence.py`, then check `evidence/` for anything private and commit it
- [ ] Write the report from `docs/REPORT_TEMPLATE.md` in your own words
- [ ] Practice the 5-minute demo twice

## Known limits to know about

- I tested the server over HTTP with a real MCP client and the auth, roles, secret-path and Host
  checks, and stdio mode (what Inspector uses) with a Python client. I did not run the Inspector
  app, ngrok or pm2 myself. You are the first to try those.
- I could not confirm whether Claude's custom connector form accepts a header token. That is why
  the secret-path URL exists.
- The `mcp` package is pinned below version 2 on purpose. Version 2 renamed FastMCP and this code
  uses the 1.x API.
- Your course brief and your own freelance-desk notes are different projects. This one follows
  the course brief. The handoff idea from your notes became the four handoff files and
  `read_state` / `append_handoff`.
