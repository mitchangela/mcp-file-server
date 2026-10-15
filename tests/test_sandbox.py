"""Path traversal tests. Every bad path must be rejected; good paths must work."""
import os

import pytest

from sandbox import Sandbox, SandboxError

BAD_PATHS = [
    "../secret.txt",
    "../../etc/passwd",
    "/etc/passwd",
    "workspace/../../x",
    "a/../../x",
    "..%2fsecret.txt",
    "%2e%2e/secret.txt",
    "..\\secret.txt",
    "a\\..\\..\\x",
    "C:\\Windows\\system.ini",
    "C:/Windows/system.ini",
    "~/secret",
    "file\x00.txt",
    ".git/config",
    "sub/.git/hooks/pre-commit",
]

GOOD_PATHS = ["", ".", "notes.md", "src/app.py", "a/b/c/d.txt", "./notes.md", "sub/../notes.md".replace("sub/../", "")]


@pytest.mark.parametrize("path", BAD_PATHS)
def test_bad_paths_rejected(ws, path):
    with pytest.raises(SandboxError):
        Sandbox(ws.workspace).resolve(path)


@pytest.mark.parametrize("path", GOOD_PATHS)
def test_good_paths_allowed(ws, path):
    resolved = Sandbox(ws.workspace).resolve(path)
    assert resolved == ws.workspace or ws.workspace in resolved.parents


@pytest.mark.skipif(os.name == "nt", reason="symlinks need admin rights on Windows")
def test_symlink_pointing_outside_is_rejected(ws, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret")
    (ws.workspace / "link").symlink_to(outside)
    sb = Sandbox(ws.workspace)
    with pytest.raises(SandboxError):
        sb.resolve("link/secret.txt")
    with pytest.raises(SandboxError):
        sb.resolve("link")


@pytest.mark.skipif(os.name == "nt", reason="symlinks need admin rights on Windows")
def test_symlink_inside_workspace_is_fine(ws):
    (ws.workspace / "real.txt").write_text("hi")
    (ws.workspace / "alias.txt").symlink_to(ws.workspace / "real.txt")
    assert Sandbox(ws.workspace).resolve("alias.txt").name == "real.txt"


def test_non_string_rejected(ws):
    with pytest.raises(SandboxError):
        Sandbox(ws.workspace).resolve(None)  # type: ignore[arg-type]
