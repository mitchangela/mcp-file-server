"""Tool behavior: read-before-write, versions, gating, roles, search, git, handoff, audit log."""
import json

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from tools import (
    append_handoff, delete_file, git_commit, git_diff, git_log, git_status,
    list_files, read_file, read_state, search_code, str_replace, write_file,
)


def version_from(read_output: str) -> str:
    return read_output.splitlines()[0].rsplit("version ", 1)[1].strip()


def test_tool_count_is_at_least_eight():
    from tools import ALL_TOOLS
    assert len(ALL_TOOLS) >= 8


def test_write_then_read(ws):
    write_file(path="notes.md", content="one\ntwo\nthree\n")
    out = read_file(path="notes.md")
    assert "lines 1-3 of 3" in out and "two" in out


def test_overwrite_requires_version(ws):
    write_file(path="a.txt", content="v1")
    with pytest.raises(ToolError, match="already exists"):
        write_file(path="a.txt", content="v2")
    v = version_from(read_file(path="a.txt"))
    write_file(path="a.txt", content="v2", if_version=v)
    assert "v2" in read_file(path="a.txt")


def test_stale_version_rejected(ws):
    write_file(path="a.txt", content="v1")
    old = version_from(read_file(path="a.txt"))
    str_replace(path="a.txt", old_str="v1", new_str="v2")
    with pytest.raises(ToolError, match="changed since"):
        write_file(path="a.txt", content="v3", if_version=old)
    with pytest.raises(ToolError, match="changed since"):
        str_replace(path="a.txt", old_str="v2", new_str="v3", if_version=old)


def test_str_replace_needs_single_match(ws):
    write_file(path="a.txt", content="x x y")
    with pytest.raises(ToolError, match="2 times"):
        str_replace(path="a.txt", old_str="x", new_str="z")
    with pytest.raises(ToolError, match="not found"):
        str_replace(path="a.txt", old_str="nope", new_str="z")
    str_replace(path="a.txt", old_str="y", new_str="z")
    assert "x x z" in read_file(path="a.txt")


def test_read_paging(ws):
    write_file(path="big.txt", content="\n".join(f"line{i}" for i in range(1, 501)))
    out = read_file(path="big.txt", offset=100, limit=5)
    assert "lines 100-104 of 500" in out and "line100" in out and "line105" not in out
    with pytest.raises(ToolError, match="past the end"):
        read_file(path="big.txt", offset=900)


def test_list_files(ws):
    write_file(path="src/app.py", content="print(1)")
    out = list_files(path=".")
    assert "src/" in out and ".git" not in out
    assert "app.py" in list_files(path="src")


def test_path_escape_is_a_clean_tool_error(ws):
    with pytest.raises(ToolError, match="escapes|'..'"):
        read_file(path="../x")
    with pytest.raises(ToolError, match="Absolute"):
        write_file(path="/tmp/x", content="no")


def test_delete_is_gated(ws):
    write_file(path="tmp.txt", content="bye")
    with pytest.raises(ToolError, match="not confirmed"):
        delete_file(path="tmp.txt")
    assert (ws.workspace / "tmp.txt").exists()
    delete_file(path="tmp.txt", confirm=True)
    assert not (ws.workspace / "tmp.txt").exists()


def test_handoff_files_cannot_be_deleted(ws):
    with pytest.raises(ToolError, match="Handoff files"):
        delete_file(path="PROJECT_STATE.md", confirm=True)


def test_directories_cannot_be_deleted(ws):
    (ws.workspace / "d").mkdir()
    with pytest.raises(ToolError, match="Only files"):
        delete_file(path="d", confirm=True)


def test_roles(ws, as_role):
    ws_fallback = ws.fallback_role
    ws.fallback_role = None
    write_file_role = as_role("admin")
    write_file(path="r.txt", content="hi")

    as_role("reader")
    assert "hi" in read_file(path="r.txt")
    with pytest.raises(ToolError, match="needs the 'writer' role"):
        write_file(path="r2.txt", content="no")

    as_role("writer")
    write_file(path="r2.txt", content="ok")
    with pytest.raises(ToolError, match="needs the 'admin' role"):
        delete_file(path="r2.txt", confirm=True)

    as_role(None)
    with pytest.raises(ToolError, match="needs the"):
        read_file(path="r.txt")
    ws.fallback_role = ws_fallback


def test_search_code(ws):
    write_file(path="src/a.py", content="def hello():\n    return 1\n")
    write_file(path="src/b.txt", content="hello there\n")
    out = search_code(query="hello", glob="*.py")
    assert "src/a.py:1" in out and "b.txt" not in out
    assert search_code(query="zzzz") == "No matches."
    assert "a.py:2" in search_code(query=r"return\s+\d", regex=True)
    with pytest.raises(ToolError, match="Invalid regex"):
        search_code(query="(", regex=True)


def test_search_result_cap(ws):
    write_file(path="many.txt", content="hit\n" * 300)
    out = search_code(query="hit", max_results=5)
    assert out.count("many.txt:") == 5 and "stopped at 5" in out


def test_git_flow(ws):
    assert "No commits yet" in git_log()
    write_file(path="f.txt", content="1")
    assert "f.txt" in git_status()
    assert "Committed" in git_commit(message="add f")
    assert "add f" in git_log()
    assert git_commit(message="again") == "Nothing to commit."
    v = version_from(read_file(path="f.txt"))
    write_file(path="f.txt", content="2", if_version=v)
    assert "+2" in git_diff(path="f.txt")


def test_git_commit_rejects_escape_and_flags(ws):
    with pytest.raises(ToolError):
        git_commit(message="x y z", paths=["../outside"])
    with pytest.raises(ToolError, match="may not start"):
        git_commit(message="--amend")


def test_read_state_and_append(ws):
    assert "===== PROJECT_STATE.md" in read_state()
    append_handoff(kind="PLAN_LOG", entry="1. scaffold\n2. test")
    append_handoff(kind="CHECKPOINTS", entry="M1 done")
    state = read_state()
    assert "scaffold" in state and "M1 done" in state
    text = (ws.workspace / "PLAN_LOG.md").read_text()
    assert text.startswith("# PLAN_LOG") and "UTC" in text  # earlier content kept


def test_read_state_trims_long_logs(ws):
    for i in range(40):
        append_handoff(kind="PLAN_LOG", entry=f"entry number {i}")
    assert "older entries trimmed" in read_state()


def test_audit_log_written(ws):
    write_file(path="x.txt", content="secret body " * 50)
    with pytest.raises(ToolError):
        read_file(path="../nope")
    lines = [json.loads(l) for l in ws.log_path.read_text().splitlines()]
    assert lines[0]["tool"] == "write_file" and lines[0]["ok"] is True
    assert "chars]" in lines[0]["args"]["content"]  # long args are shortened
    assert lines[1]["ok"] is False and "error" in lines[1]


def test_write_size_limit(ws):
    ws.max_write_bytes = 100
    with pytest.raises(ToolError, match="too large"):
        write_file(path="big.txt", content="x" * 500)
