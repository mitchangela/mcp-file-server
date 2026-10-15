"""Tool wrapper: role check, audit log, and clean errors (no stack traces to the agent)."""
from __future__ import annotations

import functools
import json
import logging
import time
from datetime import datetime, timezone

from mcp.server.fastmcp.exceptions import ToolError

from auth import current_role
from config import ROLE_ORDER, get_settings
from sandbox import SandboxError

log = logging.getLogger("mcp-file-server")


class UserError(Exception):
    """Expected problem with a plain message the agent can act on."""


def _short(value, limit: int = 120):
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + f"...[{len(value)} chars]"
    return value


def write_audit(entry: dict) -> None:
    try:
        path = get_settings().log_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:  # logging must never break a tool call
        log.exception("could not write audit log")


def tool(min_role: str):
    """Decorator: enforce a minimum role, log the call, convert errors to ToolError."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            started = time.perf_counter()
            settings = get_settings()
            role = current_role.get() or settings.fallback_role
            entry = {
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "tool": fn.__name__,
                "role": role,
                "args": {k: _short(v) for k, v in kwargs.items()},
            }
            try:
                if role is None or ROLE_ORDER[role] < ROLE_ORDER[min_role]:
                    raise UserError(
                        f"Tool '{fn.__name__}' needs the '{min_role}' role; this connection has '{role}'."
                    )
                result = fn(*args, **kwargs)
                entry["ok"] = True
                return result
            except (UserError, SandboxError) as exc:
                entry.update(ok=False, error=str(exc))
                raise ToolError(str(exc)) from None
            except Exception:  # unexpected: keep details in the server log only
                log.exception("tool %s crashed", fn.__name__)
                entry.update(ok=False, error="internal error")
                raise ToolError(
                    f"Unexpected error in '{fn.__name__}'. Check the server log."
                ) from None
            finally:
                entry["ms"] = round((time.perf_counter() - started) * 1000)
                write_audit(entry)

        return wrapper

    return decorator
