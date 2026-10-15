"""Smoke test: talks to a running server like a real MCP client.

Usage:
  python scripts/smoke_test.py http://127.0.0.1:8000/mcp  <admin-token> [reader-token]
  python scripts/smoke_test.py https://YOUR-DOMAIN/mcp    <admin-token> [reader-token]

Uses the Authorization header. The output is good evidence for the report.
"""
import asyncio
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

results = []


def check(name: str, ok: bool, detail: str = ""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


def text_of(result) -> str:
    return "".join(getattr(c, "text", "") for c in result.content)


async def run(url: str, token: str, reader_token: str | None):
    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(url, headers=headers) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = (await s.list_tools()).tools
            names = sorted(t.name for t in tools)
            check("8+ tools listed", len(tools) >= 8, f"{len(tools)}: {', '.join(names)}")

            res = await s.call_tool("read_state", {})
            check("read_state works", not res.isError and "PROJECT_STATE" in text_of(res))

            res = await s.call_tool("write_file", {"path": "smoke/hello.txt", "content": "hello\n"})
            check("write_file creates a file", not res.isError, text_of(res))

            res = await s.call_tool("write_file", {"path": "smoke/hello.txt", "content": "again\n"})
            check("overwrite without version is refused", res.isError, text_of(res))

            res = await s.call_tool("read_file", {"path": "../../etc/passwd"})
            check("path escape returns isError", res.isError, text_of(res))

            res = await s.call_tool("delete_file", {"path": "smoke/hello.txt"})
            check("delete without confirm is refused", res.isError, text_of(res))

            res = await s.call_tool("delete_file", {"path": "smoke/hello.txt", "confirm": True})
            check("delete with confirm works (admin)", not res.isError, text_of(res))

    if reader_token:
        async with streamablehttp_client(url, headers={"Authorization": f"Bearer {reader_token}"}) as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()
                res = await s.call_tool("write_file", {"path": "smoke/nope.txt", "content": "x"})
                check("reader token cannot write", res.isError, text_of(res))
                res = await s.call_tool("list_files", {})
                check("reader token can list", not res.isError)

    try:
        async with streamablehttp_client(url, headers={"Authorization": "Bearer wrong-token"}) as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()
        check("wrong token is rejected", False, "connection was accepted")
    except BaseException:
        check("wrong token is rejected", True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    asyncio.run(run(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)
