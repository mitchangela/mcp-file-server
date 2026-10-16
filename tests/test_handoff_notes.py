"""Tests for the freelance-desk handoff notes (save_handoff, load_handoff, list_handoffs)."""
import os

import pytest

from mcp.server.fastmcp.exceptions import ToolError
from config import Settings, set_settings
from tools.handoff_notes import list_handoffs, load_handoff, save_handoff

NOTE = (
    "PROJECT: Ana logo job\n"
    "GOAL: Finish the logo set\n"
    "DECISIONS MADE: Going with the blue version\n"
    "CURRENT STATE: Two drafts sent\n"
    "NEXT STEPS: Send final files\n"
    "OPEN QUESTIONS: Does she want a one-color version?"
)


@pytest.fixture
def desk(tmp_path):
    settings = Settings(
        workspace=tmp_path / "ws",
        log_path=tmp_path / "logs" / "tool_calls.jsonl",
        fallback_role="admin",
    )
    settings.workspace.mkdir()
    settings.log_path.parent.mkdir()
    set_settings(settings)
    yield settings
    set_settings(None)


def test_save_then_load(desk):
    message = save_handoff(title="Ana logo job", content=NOTE)
    assert message.startswith("Saved handoffs/")
    assert "Sections not found" not in message
    assert "Ana logo job" in load_handoff(title="ana logo job")


def test_saving_again_same_day_updates(desk):
    save_handoff(title="ana-logo", content=NOTE)
    message = save_handoff(title="ana-logo", content=NOTE + "\nNEXT STEPS: changed")
    assert message.startswith("Updated")
    assert len(list((desk.workspace / "handoffs").iterdir())) == 1


def test_missing_sections_are_reported(desk):
    message = save_handoff(title="rough", content="PROJECT: x\nGOAL: finish the thing today")
    assert "NEXT STEPS" in message


def test_title_cannot_escape_the_folder(desk):
    save_handoff(title="../../evil", content=NOTE)
    saved = list((desk.workspace / "handoffs").iterdir())
    assert len(saved) == 1
    assert saved[0].parent == desk.workspace / "handoffs"
    assert "/" not in saved[0].name and "\\" not in saved[0].name
    assert saved[0].name.endswith("_evil.txt")


def test_title_with_no_letters_rejected(desk):
    with pytest.raises(ToolError):
        save_handoff(title="///", content=NOTE)


def test_too_long_rejected(desk):
    with pytest.raises(ToolError):
        save_handoff(title="big", content="x" * 9000)


def test_load_missing_lists_known_titles(desk):
    save_handoff(title="ana-logo", content=NOTE)
    with pytest.raises(ToolError) as error:
        load_handoff(title="nothing-here")
    assert "ana-logo" in str(error.value)


def test_load_returns_newest_when_several(desk):
    folder = desk.workspace / "handoffs"
    folder.mkdir()
    old = folder / "2026-01-01_ana-logo.txt"
    new = folder / "2026-02-01_ana-logo.txt"
    old.write_text("OLD\n")
    new.write_text("NEW\n")
    assert "NEW" in load_handoff(title="ana-logo")
    assert "OLD" not in load_handoff(title="ana-logo")


def test_list_is_newest_first(desk):
    folder = desk.workspace / "handoffs"
    folder.mkdir()
    for name in ("2026-01-01_a.txt", "2026-03-01_c.txt", "2026-02-01_b.txt"):
        (folder / name).write_text("x" * 30)
    lines = list_handoffs().splitlines()
    assert [line.split()[0] for line in lines] == [
        "2026-03-01_c.txt", "2026-02-01_b.txt", "2026-01-01_a.txt",
    ]


def test_list_when_empty(desk):
    assert "No handoffs" in list_handoffs()
