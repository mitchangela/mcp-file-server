"""search_code: find text in files without reading whole files."""
from __future__ import annotations

import fnmatch
import os
import re
from typing import Annotated

from pydantic import Field

from audit import UserError, tool
from config import get_settings
from sandbox import get_sandbox

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}


@tool("reader")
def search_code(
    query: Annotated[str, Field(min_length=1, max_length=200, description="Text to find (or a regex if regex=true).")],
    path: Annotated[str, Field(description="Directory to search, relative to the workspace root.", max_length=500)] = ".",
    glob: Annotated[str, Field(description="Filename pattern, e.g. '*.py'.", max_length=100)] = "*",
    regex: Annotated[bool, Field(description="Treat query as a regular expression.")] = False,
    case_sensitive: bool = False,
    max_results: Annotated[int, Field(ge=1, le=100)] = 50,
) -> str:
    """Search text files under a directory. Returns 'path:line: text' for each match, capped at max_results."""
    sb = get_sandbox()
    root = sb.resolve(path)
    if not root.is_dir():
        raise UserError("Search path must be a directory.")
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        pattern = re.compile(query if regex else re.escape(query), flags)
    except re.error as exc:
        raise UserError(f"Invalid regex: {exc}") from None

    limit = min(max_results, get_settings().max_search_results)
    hits: list[str] = []
    truncated = False
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if not fnmatch.fnmatch(name, glob):
                continue
            file = os.path.join(dirpath, name)
            try:
                if os.path.islink(file) or os.path.getsize(file) > 1_000_000:
                    continue
                with open(file, encoding="utf-8") as fh:
                    for lineno, line in enumerate(fh, 1):
                        if pattern.search(line):
                            rel = sb.rel(sb.resolve(os.path.relpath(file, sb.root)))
                            hits.append(f"{rel}:{lineno}: {line.strip()[:200]}")
                            if len(hits) >= limit:
                                truncated = True
                                break
            except (UnicodeDecodeError, OSError):
                continue
            if truncated:
                break
        if truncated:
            break
    if not hits:
        return "No matches."
    out = "\n".join(hits)
    return out + (f"\n... stopped at {limit} results. Narrow the query or path." if truncated else "")
