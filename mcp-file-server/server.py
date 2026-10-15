"""MCP file server: entry point.

Run:  python server.py          (HTTP on HOST:PORT, needs tokens in .env)
      MCP_TRANSPORT=stdio python server.py   (local testing, e.g. MCP Inspector)
"""
from __future__ import annotations

import logging
import sys

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from auth import BearerAuthMiddleware
from config import ensure_workspace, get_settings
from tools import ALL_TOOLS, DESTRUCTIVE, READ_ONLY

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

INSTRUCTIONS = (
    "File server for a sandboxed workspace. Start each session with read_state. "
    "Read before you write: read_file gives a version, pass it as if_version when replacing. "
    "Prefer search_code and read_file with offset/limit over reading whole files. "
    "Log your plan with append_handoff(PLAN_LOG) before work and save a CHECKPOINT after each chunk."
)


def build_mcp() -> FastMCP:
    settings = get_settings()
    hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
    if settings.public_host:
        hosts.append(settings.public_host)
        origins.append(f"https://{settings.public_host}")

    mcp = FastMCP(
        "mcp-file-server",
        instructions=INSTRUCTIONS,
        host=settings.host,
        port=settings.port,
        stateless_http=True,  # each request is independent, so restarts lose nothing
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=hosts,
            allowed_origins=origins,
        ),
    )
    for fn in ALL_TOOLS:
        annotations = ToolAnnotations(
            readOnlyHint=fn.__name__ in READ_ONLY,
            destructiveHint=fn.__name__ in DESTRUCTIVE,
        )
        mcp.tool(annotations=annotations)(fn)
    return mcp


def build_app():
    """ASGI app for uvicorn: the MCP endpoint wrapped in token auth."""
    settings = get_settings()
    if not settings.tokens:
        sys.exit("No tokens set. Add MCP_TOKEN_ADMIN (and optionally _WRITER / _READER) to .env.")
    weak = [r for r, t in settings.tokens.items() if len(t) < 24]
    if weak:
        sys.exit(f"Token(s) for {weak} are too short. Use at least 24 random characters.")
    ensure_workspace()
    return BearerAuthMiddleware(build_mcp().streamable_http_app())


if __name__ == "__main__":
    cfg = get_settings()
    if cfg.transport == "stdio":
        ensure_workspace()
        build_mcp().run(transport="stdio")
    else:
        import uvicorn

        uvicorn.run(build_app(), host=cfg.host, port=cfg.port, log_level="info")
