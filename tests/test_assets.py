"""Tests for the asset librarian. The design folders are never changed by any tool."""
import os
import time
from datetime import datetime
from pathlib import Path

import pytest

from mcp.server.fastmcp.exceptions import ToolError
from config import Settings, set_settings
from tools.assets import find_by_client, list_recent, reindex, search_assets, tag_asset


def make_file(path: Path, text="x", when=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if when:
        stamp = time.mktime(when.timetuple())
        os.utime(path, (stamp, stamp))
    return path


@pytest.fixture
def admin(tmp_path, monkeypatch):
    """Settings with the admin role, and a private index file. No asset folders set yet."""
    settings = Settings(
        workspace=tmp_path / "ws",
        log_path=tmp_path / "logs" / "tool_calls.jsonl",
        fallback_role="admin",
    )
    settings.workspace.mkdir()
    settings.log_path.parent.mkdir()
    set_settings(settings)
    monkeypatch.delenv("ASSET_ROOTS", raising=False)
    monkeypatch.setenv("ASSET_DB", str(tmp_path / "assets.db"))
    yield tmp_path
    set_settings(None)


@pytest.fixture
def library(admin, monkeypatch):
    root = admin / "designs"
    root.mkdir()
    monkeypatch.setenv("ASSET_ROOTS", str(root))
    return root


def test_not_configured(admin):
    with pytest.raises(ToolError):
        reindex()


def test_refuses_home_folder(admin, monkeypatch):
    monkeypatch.setenv("ASSET_ROOTS", str(admin))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: admin))
    with pytest.raises(ToolError):
        reindex()


def test_reindex_skips_junk_and_hidden(library):
    make_file(library / "posters" / "gdg-poster.png")
    make_file(library / "node_modules" / "pkg" / "junk.png")
    make_file(library / "posters" / ".hidden.png")
    make_file(library / "posters" / "Thumbs.db")
    result = reindex()
    assert "1 new" in result
    assert "gdg-poster.png" in list_recent()
    assert "junk.png" not in list_recent()


def test_reindex_is_incremental_and_removes_gone_files(library):
    keep = make_file(library / "keep.png", "aaa")
    gone = make_file(library / "gone.png")
    reindex()
    gone.unlink()
    make_file(library / "new.png")
    result = reindex()
    assert "1 new" in result and "1 removed" in result
    assert "gone.png" not in list_recent()
    assert keep.exists()  # the library never touches design files


def test_files_are_never_changed(library):
    path = make_file(library / "logo.psd", "original")
    before = (path.read_text(), path.stat().st_mtime_ns)
    reindex()
    tag_asset(path=str(path), tags=["logo"], client="Ana")
    assert (path.read_text(), path.stat().st_mtime_ns) == before


def test_search_by_name_and_type(library):
    make_file(library / "ana-logo-final.png")
    make_file(library / "ana-logo-final.psd")
    reindex()
    assert "ana-logo-final.png" in search_assets(query="logo")
    only_psd = search_assets(query="logo", file_type="psd")
    assert ".psd" in only_psd and ".png" not in only_psd


def test_search_by_month(library):
    make_file(library / "blue-poster.png", when=datetime(2026, 8, 14, 12, 0))
    make_file(library / "red-poster.png", when=datetime(2026, 3, 2, 12, 0))
    reindex()
    result = search_assets(query="that poster from August")
    assert "blue-poster.png" in result and "red-poster.png" not in result
    assert "red-poster.png" in search_assets(query="poster 2026-03")


def test_search_needs_something(library):
    with pytest.raises(ToolError):
        search_assets(query="the my a")


def test_search_with_no_matches_is_not_an_error(library):
    make_file(library / "a.png")
    reindex()
    assert "No matches" in search_assets(query="zzz")


def test_tag_one_file_then_search_by_tag(library):
    path = make_file(library / "final_v3_REAL.png")
    reindex()
    assert "Updated 1" in tag_asset(path=str(path), tags=["Poster", "Blue", "poster"])
    result = search_assets(query="blue")
    assert "final_v3_REAL.png" in result and "tags: poster,blue" in result


def test_tag_a_whole_folder(library):
    make_file(library / "gdg" / "a.png")
    make_file(library / "gdg" / "sub" / "b.png")
    make_file(library / "other" / "c.png")
    reindex()
    assert "Updated 2" in tag_asset(path=str(library / "gdg"), tags=["gdg"])
    result = search_assets(query="gdg")
    assert "a.png" in result and "b.png" in result and "c.png" not in result


def test_client_links(library):
    make_file(library / "ana" / "logo.png")
    make_file(library / "ben" / "logo.png")
    reindex()
    tag_asset(path=str(library / "ana"), client="Ana")
    result = find_by_client(name="ana")
    assert "ana" in result.lower() and "ben" not in result
    assert "No files" in find_by_client(name="nobody")


def test_tag_needs_something_and_an_indexed_path(library):
    path = make_file(library / "a.png")
    reindex()
    with pytest.raises(ToolError):
        tag_asset(path=str(path))
    with pytest.raises(ToolError):
        tag_asset(path=str(library / "not-indexed.png"), tags=["x"])


def test_bad_tag_rejected(library):
    path = make_file(library / "a.png")
    reindex()
    with pytest.raises(ToolError):
        tag_asset(path=str(path), tags=["a,b"])


def test_tags_and_client_survive_reindex(library):
    path = make_file(library / "a.png", "one")
    reindex()
    tag_asset(path=str(path), tags=["keep"], client="Ana")
    make_file(library / "a.png", "changed and longer")
    result = reindex()
    assert "1 updated" in result
    assert "tags: keep" in search_assets(query="keep") and "client: Ana" in search_assets(query="keep")
