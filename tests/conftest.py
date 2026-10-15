import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from auth import current_role  # noqa: E402


@pytest.fixture
def ws(tmp_path):
    """A fresh workspace with seeded handoff files and its own git repo."""
    settings = config.Settings(
        workspace=(tmp_path / "workspace").resolve(),
        log_path=tmp_path / "logs" / "calls.jsonl",
        tokens={"admin": "a" * 32, "writer": "w" * 32, "reader": "r" * 32},
        fallback_role="admin",
    )
    config.set_settings(settings)
    config.ensure_workspace(settings)
    yield settings
    config.set_settings(None)


@pytest.fixture
def as_role():
    def _set(role):
        return current_role.set(role)

    yield _set
    current_role.set(None)
