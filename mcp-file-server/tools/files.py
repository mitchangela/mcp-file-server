"""File tools. All paths are relative to the workspace root."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Annotated

from pydantic import Field

from audit import UserError, tool
from config import HANDOFF_FILES, get_settings
from sandbox import get_sandbox

PathArg = Annotated[str, Field(description="Path relative to the workspace root, e.g. 'src/app.py'.", max_length=500)]
VersionArg = Annotated[
    str | None,
    Field(description="Version string from read_file. The write is refused if the file changed since.", max_length=32),
]


def version_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def read_text_file(path: Path) -> tuple[str, bytes]:
    if not path.exists():
        raise UserError("File not found. Use list_files to see what exists.")
    if not path.is_file():
        raise UserError("That path is a directory, not a file.")
    data = path.read_bytes()
    try:
        return data.decode("utf-8"), data
    except UnicodeDecodeError:
        raise UserError("File is not UTF-8 text, so it cannot be read here.") from None


def atomic_write(path: Path, text: str) -> str:
    data = text.encode("utf-8")
    if len(data) > get_settings().max_write_bytes:
        raise UserError(f"Content is too large (limit {get_settings().max_write_bytes} bytes).")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return version_of(data)


@tool("reader")
def list_files(
    path: PathArg = ".",
    max_entries: Annotated[int, Field(ge=1, le=500, description="Maximum entries to return.")] = 200,
) -> str:
    """List the files and folders directly inside a directory (not recursive). Directories end with '/'."""
    sb = get_sandbox()
    target = sb.resolve(path)
    if not target.exists():
        raise UserError("Directory not found.")
    if not target.is_dir():
        raise UserError("That path is a file. Use read_file instead.")
    entries = sorted(
        (e for e in target.iterdir() if e.name != ".git"),
        key=lambda e: (not e.is_dir(), e.name.lower()),
    )
    lines = []
    for e in entries[:max_entries]:
        lines.append(f"{e.name}/" if e.is_dir() else f"{e.name}  ({e.stat().st_size} bytes)")
    if len(entries) > max_entries:
        lines.append(f"... {len(entries) - max_entries} more not shown")
    return "\n".join(lines) if lines else "(empty directory)"


@tool("reader")
def read_file(
    path: PathArg,
    offset: Annotated[int, Field(ge=1, description="First line to read (1-based).")] = 1,
    limit: Annotated[int, Field(ge=1, le=400, description="Number of lines to read.")] = 200,
) -> str:
    """Read part of a text file. Returns a header with the file's version, then the lines.
    Use offset/limit to page through big files, or search_code to find the right spot first."""
    sb = get_sandbox()
    text, data = read_text_file(sb.resolve(path))
    lines = text.splitlines()
    limit = min(limit, get_settings().max_read_lines)
    chunk = lines[offset - 1 : offset - 1 + limit]
    if not chunk and lines:
        raise UserError(f"Offset {offset} is past the end of the file ({len(lines)} lines).")
    end = offset - 1 + len(chunk)
    header = f"# {sb.rel(sb.resolve(path))} | lines {offset}-{end} of {len(lines)} | version {version_of(data)}"
    return header + "\n" + "\n".join(chunk)


@tool("writer")
def write_file(
    path: PathArg,
    content: Annotated[str, Field(description="Full new content of the file.")],
    if_version: VersionArg = None,
) -> str:
    """Create a new file, or replace an existing one. To replace an existing file you must pass
    if_version from read_file. For small edits prefer str_replace."""
    sb = get_sandbox()
    target = sb.resolve(path)
    if target.is_dir():
        raise UserError("That path is a directory.")
    if target.exists():
        if if_version is None:
            raise UserError(
                "File already exists. Read it first and pass if_version, or use str_replace for a small edit."
            )
        _, data = read_text_file(target)
        if version_of(data) != if_version:
            raise UserError("File changed since you read it. Read it again and retry with the new version.")
    new_version = atomic_write(target, content)
    return f"Wrote {sb.rel(target)} ({len(content.encode('utf-8'))} bytes). New version {new_version}."


@tool("writer")
def str_replace(
    path: PathArg,
    old_str: Annotated[str, Field(min_length=1, description="Exact text to replace. Must appear exactly once.")],
    new_str: Annotated[str, Field(description="Replacement text. Empty string deletes the match.")],
    if_version: VersionArg = None,
) -> str:
    """Replace one exact piece of text in a file. Fails if the text is missing or appears more than once."""
    sb = get_sandbox()
    target = sb.resolve(path)
    text, data = read_text_file(target)
    if if_version is not None and version_of(data) != if_version:
        raise UserError("File changed since you read it. Read it again and retry with the new version.")
    count = text.count(old_str)
    if count == 0:
        raise UserError("old_str was not found. Check whitespace and read the file again.")
    if count > 1:
        raise UserError(f"old_str appears {count} times. Add surrounding text so it matches once.")
    new_version = atomic_write(target, text.replace(old_str, new_str, 1))
    return f"Edited {sb.rel(target)}. New version {new_version}."


@tool("admin")
def delete_file(
    path: PathArg,
    confirm: Annotated[bool, Field(description="Must be true. Deleting cannot be undone from here.")] = False,
) -> str:
    """Delete one file (never a directory). Requires confirm=true and the admin role.
    The four handoff files cannot be deleted."""
    sb = get_sandbox()
    target = sb.resolve(path)
    if not confirm:
        raise UserError("Deletion not confirmed. Call again with confirm=true if you are sure.")
    if not target.exists():
        raise UserError("File not found.")
    if not target.is_file():
        raise UserError("Only files can be deleted, not directories.")
    if sb.rel(target) in HANDOFF_FILES:
        raise UserError("Handoff files cannot be deleted.")
    target.unlink()
    return f"Deleted {sb.rel(target)}."
