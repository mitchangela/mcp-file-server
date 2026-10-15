"""Path sandbox. Every path from a tool goes through Sandbox.resolve()."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from config import get_settings

PROTECTED_PARTS = {".git"}  # agents must not touch git internals (hooks, config)


class SandboxError(Exception):
    """A path was rejected. The message is safe to show to the agent."""


class Sandbox:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def resolve(self, raw: str) -> Path:
        if not isinstance(raw, str):
            raise SandboxError("Path must be a string.")
        if "\x00" in raw:
            raise SandboxError("Path contains a null byte.")

        rel = raw.strip().replace("\\", "/")
        decoded = unquote(rel)
        # Encoded tricks like ..%2f are rejected instead of guessed at.
        if decoded != rel and (".." in decoded.split("/") or decoded.startswith("/")):
            raise SandboxError("Encoded path traversal is not allowed.")
        if rel.startswith("/") or rel.startswith("~") or re.match(r"^[A-Za-z]:", rel):
            raise SandboxError(
                "Absolute paths are not allowed. Use a path relative to the workspace root."
            )
        if ".." in rel.split("/"):
            raise SandboxError("Path may not contain '..'.")

        candidate = (self.root / rel).resolve()  # follows symlinks
        if candidate != self.root and self.root not in candidate.parents:
            raise SandboxError("Path escapes the workspace root.")
        if PROTECTED_PARTS & set(candidate.relative_to(self.root).parts):
            raise SandboxError("Access to .git internals is not allowed.")
        return candidate

    def rel(self, path: Path) -> str:
        r = path.resolve().relative_to(self.root).as_posix()
        return r or "."


def get_sandbox() -> Sandbox:
    return Sandbox(get_settings().workspace)
