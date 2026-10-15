"""git-lite: a few safe git commands, run inside the workspace repo only."""
from __future__ import annotations

import os
import subprocess
from typing import Annotated

from pydantic import Field

from audit import UserError, tool
from config import get_settings
from sandbox import get_sandbox

MAX_OUTPUT_LINES = 200


def run_git(*args: str) -> str:
    settings = get_settings()
    cmd = [
        "git",
        "-c", "user.name=" + os.environ.get("GIT_AUTHOR_NAME", "mcp-agent"),
        "-c", "user.email=" + os.environ.get("GIT_AUTHOR_EMAIL", "mcp-agent@localhost"),
        *args,
    ]
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        proc = subprocess.run(
            cmd, cwd=settings.workspace, capture_output=True, text=True, timeout=20, env=env
        )
    except FileNotFoundError:
        raise UserError("git is not installed on the server.") from None
    except subprocess.TimeoutExpired:
        raise UserError("git took too long and was stopped.") from None
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout).strip().splitlines()
        raise UserError("git failed: " + (msg[0] if msg else "unknown error"))
    out = proc.stdout.strip().splitlines()
    if len(out) > MAX_OUTPUT_LINES:
        out = out[:MAX_OUTPUT_LINES] + [f"... output cut at {MAX_OUTPUT_LINES} lines"]
    return "\n".join(out)


@tool("reader")
def git_status() -> str:
    """Show the current branch and which files are changed or untracked in the workspace repo."""
    return run_git("status", "--short", "--branch")


@tool("reader")
def git_diff(
    path: Annotated[str | None, Field(description="Limit the diff to one file.", max_length=500)] = None,
    staged: Annotated[bool, Field(description="Show staged changes instead of unstaged.")] = False,
) -> str:
    """Show line changes in the workspace repo (output is capped at 200 lines)."""
    args = ["diff"] + (["--staged"] if staged else [])
    if path:
        sb = get_sandbox()
        args += ["--", sb.rel(sb.resolve(path))]
    return run_git(*args) or "No changes."


@tool("reader")
def git_log(
    max_count: Annotated[int, Field(ge=1, le=50, description="How many commits to show.")] = 10,
) -> str:
    """Show recent commits, one line each."""
    try:
        return run_git("log", f"--max-count={max_count}", "--oneline", "--decorate")
    except UserError:
        return "No commits yet."


@tool("writer")
def git_commit(
    message: Annotated[str, Field(min_length=3, max_length=200, description="Commit message, one line.")],
    paths: Annotated[list[str] | None, Field(description="Files to commit. Leave empty to commit all changes.", max_length=50)] = None,
) -> str:
    """Stage and commit changes in the workspace repo. Does nothing if there is nothing to commit."""
    if message.startswith("-"):
        raise UserError("Commit message may not start with '-'.")
    sb = get_sandbox()
    if paths:
        rels = [sb.rel(sb.resolve(p)) for p in paths]
        run_git("add", "--", *rels)
    else:
        run_git("add", "-A")
    if not run_git("diff", "--staged", "--name-only"):
        return "Nothing to commit."
    run_git("commit", "-m", message)
    return "Committed: " + run_git("log", "-1", "--oneline")
