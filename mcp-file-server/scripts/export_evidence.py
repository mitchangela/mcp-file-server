"""Copy the handoff files, audit log and workspace git history into evidence/.
Run after your demo, then commit evidence/. Check the files for anything private first."""
import shutil
import subprocess
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import HANDOFF_FILES, get_settings  # noqa: E402

s = get_settings()
out = Path(__file__).resolve().parent.parent / "evidence"
out.mkdir(exist_ok=True)

for name in HANDOFF_FILES:
    src = s.workspace / name
    if src.exists():
        shutil.copyfile(src, out / name)
        print("copied", name)

if s.log_path.exists():
    shutil.copyfile(s.log_path, out / "tool_calls.jsonl")
    print("copied tool_calls.jsonl")

if (s.workspace / ".git").exists():
    log = subprocess.run(
        ["git", "log", "--stat", "--date=iso"], cwd=s.workspace, capture_output=True, text=True
    ).stdout
    (out / "workspace_git_log.txt").write_text(log, encoding="utf-8")
    print("wrote workspace_git_log.txt")
