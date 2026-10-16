"""Freelance-desk handoff notes: save a short summary, load it in a new chat.

Not the same as tools/handoff.py (PROJECT_STATE / PLAN_LOG protocol). These notes are
free-form summaries, one txt file each, kept in workspace/handoffs/.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated

from pydantic import Field

from audit import UserError, tool
from config import get_settings
from tools.files import atomic_write, read_text_file

FOLDER = "handoffs"
MAX_CHARS = 8000
MIN_CHARS = 20
SECTIONS = ("PROJECT", "GOAL", "DECISIONS MADE", "CURRENT STATE", "NEXT STEPS", "OPEN QUESTIONS")
_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})_(.+)\.txt$")


def _folder():
    return get_settings().workspace / FOLDER


def _slug(title: str) -> str:
    """Turn a title into a safe file-name part. Letters, digits and dashes only."""
    text = title.strip()
    text = re.sub(r"\.txt$", "", text, flags=re.I)
    text = re.sub(r"^\d{4}-\d{2}-\d{2}[_ -]+", "", text)
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60].strip("-")
    if not slug:
        raise UserError("Give the handoff a short title that has letters or numbers in it.")
    return slug


def _saved():
    """Saved handoffs as (path, slug), unsorted."""
    folder = _folder()
    if not folder.is_dir():
        return []
    items = []
    for path in folder.iterdir():
        match = _NAME.match(path.name)
        if match and path.is_file():
            items.append((path, match.group(2)))
    return items


def _newest_first(items):
    return sorted(items, key=lambda i: (i[0].name[:10], i[0].stat().st_mtime), reverse=True)


@tool("writer")
def save_handoff(
    title: Annotated[str, Field(min_length=1, max_length=80, description="Short name for this handoff, like 'ana-logo-job'.")],
    content: Annotated[str, Field(min_length=MIN_CHARS, max_length=MAX_CHARS, description="The summary you wrote, using the six sections.")],
) -> str:
    """Save a short summary of this conversation so a new chat can pick it up. Write the summary
    yourself first, keep it to about 20 lines, and use these sections:
    PROJECT: / GOAL: / DECISIONS MADE: / CURRENT STATE: / NEXT STEPS: / OPEN QUESTIONS:
    Saving again with the same title on the same day updates that file."""
    slug = _slug(title)
    text = content.strip()
    if len(text) < MIN_CHARS:
        raise UserError("That handoff is too short to be useful. Use the six sections.")
    if len(text) > MAX_CHARS:
        raise UserError(
            f"That handoff is {len(text)} characters. Keep it under {MAX_CHARS}: a short summary works better than a transcript."
        )
    folder = _folder()
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{datetime.now():%Y-%m-%d}_{slug}.txt"
    path = folder / name
    existed = path.exists()
    atomic_write(path, text + "\n")
    missing = [s for s in SECTIONS if not re.search(rf"^{re.escape(s)}\s*:", text, re.M | re.I)]
    message = f"{'Updated' if existed else 'Saved'} {FOLDER}/{name} ({len(text)} characters)."
    if missing:
        message += " Sections not found: " + ", ".join(missing) + "."
    return message


@tool("reader")
def load_handoff(
    title: Annotated[str, Field(min_length=1, max_length=80, description="The handoff title. The newest match is returned.")],
) -> str:
    """Load a saved handoff by title and return its text, so you can continue that work.
    If several match, the newest one is returned."""
    slug = _slug(title)
    items = _saved()
    pool = [i for i in items if i[1] == slug] or [i for i in items if slug in i[1]]
    if not pool:
        known = ", ".join(sorted({i[1] for i in items})[:10])
        hint = f" Saved titles: {known}." if known else " Nothing is saved yet."
        raise UserError(f"No handoff matches '{title}'.{hint}")
    path, _ = _newest_first(pool)[0]
    text, _version = read_text_file(path)
    return f"[{FOLDER}/{path.name}]\n{text.strip()}"


@tool("reader")
def list_handoffs(
    limit: Annotated[int, Field(ge=1, le=100, description="How many to list.")] = 20,
) -> str:
    """List saved handoffs, newest first."""
    items = _newest_first(_saved())
    if not items:
        return "No handoffs saved yet."
    lines = [f"{p.name}  ({p.stat().st_size} bytes)" for p, _ in items[:limit]]
    extra = len(items) - limit
    if extra > 0:
        lines.append(f"(+{extra} older)")
    return "\n".join(lines)
