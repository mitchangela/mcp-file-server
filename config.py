"""Settings, read from environment variables (and .env if python-dotenv is installed)."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:  # optional, so tests and Docker work without it
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # pragma: no cover
    pass

ROLE_ORDER = {"reader": 1, "writer": 2, "admin": 3}
HANDOFF_FILES = ("PROJECT_STATE.md", "PLAN_LOG.md", "CHECKPOINTS.md", "DECISIONS.md")


@dataclass
class Settings:
    workspace: Path
    log_path: Path
    tokens: dict[str, str] = field(default_factory=dict)  # role -> secret
    host: str = "127.0.0.1"
    port: int = 8000
    public_host: str = ""  # e.g. my-name.ngrok-free.dev
    transport: str = "http"  # "http" or "stdio"
    fallback_role: str | None = None  # role used when no HTTP auth ran (stdio, tests)
    max_read_lines: int = 400
    max_write_bytes: int = 1_000_000
    max_search_results: int = 100


def load_settings(env=os.environ) -> Settings:
    workspace = Path(env.get("WORKSPACE_ROOT", str(BASE_DIR / "workspace"))).expanduser()
    if not workspace.is_absolute():
        workspace = BASE_DIR / workspace
    log_path = Path(env.get("AUDIT_LOG", str(BASE_DIR / "logs" / "tool_calls.jsonl")))
    if not log_path.is_absolute():
        log_path = BASE_DIR / log_path

    tokens = {}
    for role in ROLE_ORDER:
        value = env.get(f"MCP_TOKEN_{role.upper()}", "").strip()
        if value:
            tokens[role] = value

    transport = env.get("MCP_TRANSPORT", "http").strip().lower()
    return Settings(
        workspace=workspace.resolve(),
        log_path=log_path,
        tokens=tokens,
        host=env.get("HOST", "127.0.0.1"),
        port=int(env.get("PORT", "8000")),
        public_host=env.get("PUBLIC_HOST", "").strip(),
        transport=transport,
        fallback_role="admin" if transport == "stdio" else None,
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def set_settings(settings: Settings | None) -> None:
    """Used by tests to swap settings."""
    global _settings
    _settings = settings


def ensure_workspace(settings: Settings | None = None) -> None:
    """Create the workspace, seed the four handoff files, and init its git repo."""
    import subprocess

    s = settings or get_settings()
    s.workspace.mkdir(parents=True, exist_ok=True)
    s.log_path.parent.mkdir(parents=True, exist_ok=True)
    for name in HANDOFF_FILES:
        target = s.workspace / name
        template = BASE_DIR / "templates" / name
        if not target.exists() and template.exists():
            shutil.copyfile(template, target)
    if not (s.workspace / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=s.workspace, check=False, timeout=20)
