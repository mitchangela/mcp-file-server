"""Handoff protocol tools: PROJECT_STATE, PLAN_LOG, CHECKPOINTS, DECISIONS."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import Field

from audit import UserError, tool
from config import get_settings
from tools.files import atomic_write, read_text_file

TAIL_LINES = 30


def _tail(text: str, n: int) -> str:
    lines = text.splitlines()
    if len(lines) <= n:
        return text.strip()
    return f"(older entries trimmed, showing last {n} lines)\n" + "\n".join(lines[-n:])


@tool("reader")
def read_state() -> str:
    """Start every session with this. Returns PROJECT_STATE in full plus the latest entries of
    PLAN_LOG, CHECKPOINTS and DECISIONS in one call."""
    root = get_settings().workspace
    parts = []
    for name in ("PROJECT_STATE.md", "PLAN_LOG.md", "CHECKPOINTS.md", "DECISIONS.md"):
        path = root / name
        if not path.exists():
            parts.append(f"===== {name} =====\n(missing)")
            continue
        text, _ = read_text_file(path)
        body = text.strip() if name == "PROJECT_STATE.md" else _tail(text, TAIL_LINES)
        parts.append(f"===== {name} =====\n{body}")
    return "\n\n".join(parts)


@tool("writer")
def append_handoff(
    kind: Annotated[Literal["PLAN_LOG", "CHECKPOINTS", "DECISIONS"], Field(description="Which log to add to.")],
    entry: Annotated[str, Field(min_length=3, max_length=2000, description="The entry text. A UTC timestamp is added for you.")],
) -> str:
    """Add a timestamped entry to the end of PLAN_LOG, CHECKPOINTS or DECISIONS. Append-only, so
    earlier entries are never lost. Update PROJECT_STATE with str_replace instead."""
    path = get_settings().workspace / f"{kind}.md"
    existing = ""
    if path.exists():
        existing, _ = read_text_file(path)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    new_text = existing.rstrip("\n") + f"\n\n## {stamp}\n{entry.strip()}\n"
    atomic_write(path, new_text)
    return f"Added entry to {kind}.md."
