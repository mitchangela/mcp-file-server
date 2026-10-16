"""Asset librarian (stages 1-2): a search index of my design folders.

Read-only on the design folders: it only looks at file names, sizes and dates. It never opens,
moves, renames or deletes a file. Tags and client links live in a SQLite index, not on the files.

Setup: put the folders to index in .env, separated by ';':
    ASSET_ROOTS=C:\\Users\\me\\Designs;D:\\Client Work
Then call reindex. With ASSET_ROOTS empty, every tool here says so and does nothing.
"""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated

from pydantic import Field

from audit import UserError, tool
from config import BASE_DIR

JUNK_DIRS = {
    "node_modules", "__pycache__", "cache", "caches", ".cache", "tmp", "temp", ".tmp",
    "venv", ".venv", "$recycle.bin", "system volume information", ".trash", ".git",
}
JUNK_FILES = {"thumbs.db", ".ds_store", "desktop.ini"}
MAX_FILES = 100_000
MAX_TAG_TARGETS = 5000
MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4, "apr": 4,
    "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9, "october": 10, "oct": 10, "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}
STOPWORDS = {"the", "a", "an", "my", "of", "from", "in", "that", "i", "made", "file", "files", "one", "for"}
_TAG = re.compile(r"^[a-z0-9][a-z0-9 _-]{0,29}$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
  path_key TEXT PRIMARY KEY,
  path TEXT NOT NULL,
  filename TEXT NOT NULL,
  type TEXT NOT NULL,
  size INTEGER NOT NULL,
  created TEXT NOT NULL,
  modified TEXT NOT NULL,
  mtime_ns INTEGER NOT NULL,
  tags TEXT NOT NULL DEFAULT '',
  client TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_assets_modified ON assets(modified);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(type);
"""


# ---------- setup helpers ----------

def _db_path() -> Path:
    raw = os.environ.get("ASSET_DB", "").strip()
    path = Path(raw).expanduser() if raw else BASE_DIR / "data" / "assets.db"
    return path if path.is_absolute() else BASE_DIR / path


@contextmanager
def _db():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _roots() -> list[Path]:
    raw = os.environ.get("ASSET_ROOTS", "").strip()
    if not raw:
        raise UserError("No asset folders are set. Add ASSET_ROOTS to .env (full paths separated by ';'), then call reindex.")
    roots: list[Path] = []
    for part in raw.split(";"):
        part = part.strip().strip('"')
        if not part:
            continue
        path = Path(part).expanduser()
        if not path.is_absolute():
            raise UserError(f"ASSET_ROOTS needs full folder paths. Not a full path: {part}")
        path = path.resolve()
        if path == path.parent or path == Path.home().resolve():
            raise UserError(f"Refusing to index {path}. Pick a design folder, not a drive root or your home folder.")
        if not path.is_dir():
            raise UserError(f"Asset folder not found: {path}")
        roots.append(path)
    if not roots:
        raise UserError("ASSET_ROOTS is empty. Add at least one folder.")
    return roots


def _key(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def _stamp(seconds: float) -> str:
    return datetime.fromtimestamp(seconds).strftime("%Y-%m-%d %H:%M")


def _is_junk_dir(name: str) -> bool:
    return name.lower() in JUNK_DIRS


def _human(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def _format(rows) -> str:
    lines = []
    for r in rows:
        extra = ""
        if r["tags"]:
            extra += f" | tags: {r['tags']}"
        if r["client"]:
            extra += f" | client: {r['client']}"
        lines.append(f"{r['path']}  [{r['type'] or 'no ext'}, {_human(r['size'])}, modified {r['modified']}]{extra}")
    return "\n".join(lines)


# ---------- indexing (admin) ----------

@tool("admin")
def reindex() -> str:
    """Rescan the folders in ASSET_ROOTS and update the index. Only file names, sizes and dates are
    read. Files are never opened, moved or deleted. Only new or changed files are updated, and
    existing tags and client links are kept. Junk folders (node_modules, caches, temp) are skipped."""
    roots = _roots()
    seen: set[str] = set()
    added = updated = 0
    truncated = False
    with _db() as conn:
        known = {r["path_key"]: (r["size"], r["mtime_ns"]) for r in conn.execute("SELECT path_key, size, mtime_ns FROM assets")}
        for root in roots:
            for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
                dirnames[:] = [d for d in dirnames if not _is_junk_dir(d)]
                for name in filenames:
                    if name.startswith(".") or name.lower() in JUNK_FILES:
                        continue
                    if len(seen) >= MAX_FILES:
                        truncated = True
                        break
                    full = os.path.join(dirpath, name)
                    try:
                        if os.path.islink(full):
                            continue
                        stat = os.stat(full)
                    except OSError:
                        continue
                    key = _key(full)
                    seen.add(key)
                    row = (
                        full, name, os.path.splitext(name)[1].lower().lstrip("."), stat.st_size,
                        _stamp(stat.st_ctime), _stamp(stat.st_mtime), stat.st_mtime_ns,
                    )
                    if key not in known:
                        conn.execute(
                            "INSERT INTO assets (path, filename, type, size, created, modified, mtime_ns, path_key) VALUES (?,?,?,?,?,?,?,?)",
                            row + (key,),
                        )
                        added += 1
                    elif known[key] != (stat.st_size, stat.st_mtime_ns):
                        conn.execute(
                            "UPDATE assets SET path=?, filename=?, type=?, size=?, created=?, modified=?, mtime_ns=? WHERE path_key=?",
                            row + (key,),
                        )
                        updated += 1
                if truncated:
                    break
            if truncated:
                break
        removed = 0
        if not truncated:
            gone = [k for k in known if k not in seen]
            conn.executemany("DELETE FROM assets WHERE path_key=?", [(k,) for k in gone])
            removed = len(gone)
        total = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    message = f"Indexed {len(roots)} folder(s): {added} new, {updated} updated, {removed} removed from the index. {total} files in the index."
    if truncated:
        message += f" Stopped at {MAX_FILES} files, so nothing was removed. Use smaller folders."
    return message


# ---------- search (reader) ----------

def _parse_query(query: str):
    words: list[str] = []
    month = year = None
    for token in re.split(r"[\s,]+", query.lower().strip()):
        if not token or token in STOPWORDS:
            continue
        if token in MONTHS:
            month = MONTHS[token]
        elif re.fullmatch(r"(19|20)\d{2}-(0[1-9]|1[0-2])", token):
            year, month = int(token[:4]), int(token[5:])
        elif re.fullmatch(r"(19|20)\d{2}", token):
            year = int(token)
        else:
            words.append(token)
    return words, month, year


@tool("reader")
def search_assets(
    query: Annotated[str, Field(min_length=1, max_length=200, description="Words from the file name, a tag, or a client, plus an optional month or year. Example: 'poster august' or 'gdg 2026'.")],
    file_type: Annotated[str | None, Field(max_length=10, description="Optional file type, like png, psd, ai, pdf.")] = None,
    limit: Annotated[int, Field(ge=1, le=100, description="Most results to return.")] = 20,
) -> str:
    """Find design files by name, tag, client or date. A month or year in the query filters by the
    file's modified date. Words match file names, tags and client names. Colors and looks can't be
    searched yet unless they're in the name or a tag."""
    words, month, year = _parse_query(query)
    if not words and month is None and year is None:
        raise UserError("Give a word from the file name, a tag, a client, or a month/year. For the newest files use list_recent.")
    _roots()
    clauses, params = [], []
    for word in words:
        clauses.append("instr(lower(filename || ' ' || tags || ' ' || client), ?) > 0")
        params.append(word)
    if month is not None:
        clauses.append("CAST(substr(modified, 6, 2) AS INTEGER) = ?")
        params.append(month)
    if year is not None:
        clauses.append("substr(modified, 1, 4) = ?")
        params.append(str(year))
    if file_type:
        clauses.append("type = ?")
        params.append(file_type.lower().lstrip("."))
    sql = f"SELECT * FROM assets WHERE {' AND '.join(clauses)} ORDER BY modified DESC LIMIT ?"
    with _db() as conn:
        rows = conn.execute(sql, params + [limit]).fetchall()
    if not rows:
        return "No matches. Try fewer words, or call reindex if the files are new."
    return _format(rows)


@tool("reader")
def list_recent(
    file_type: Annotated[str | None, Field(max_length=10, description="Optional file type, like png, psd, ai, pdf.")] = None,
    limit: Annotated[int, Field(ge=1, le=100, description="How many files.")] = 10,
) -> str:
    """List the most recently modified design files, optionally only one file type."""
    _roots()
    sql, params = "SELECT * FROM assets", []
    if file_type:
        sql += " WHERE type = ?"
        params.append(file_type.lower().lstrip("."))
    sql += " ORDER BY modified DESC LIMIT ?"
    with _db() as conn:
        rows = conn.execute(sql, params + [limit]).fetchall()
    if not rows:
        return "Nothing in the index yet. Call reindex first."
    return _format(rows)


@tool("reader")
def find_by_client(
    name: Annotated[str, Field(min_length=1, max_length=60, description="Client name, or part of it.")],
    limit: Annotated[int, Field(ge=1, le=100, description="Most files to return.")] = 50,
) -> str:
    """List all files linked to a client. Links are set with tag_asset."""
    _roots()
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM assets WHERE instr(lower(client), ?) > 0 ORDER BY modified DESC LIMIT ?",
            (name.strip().lower(), limit),
        ).fetchall()
    if not rows:
        return f"No files are linked to '{name}'. Link files with tag_asset."
    return _format(rows)


# ---------- tags and client links (writer) ----------

def _clean_tags(tags: list[str]) -> list[str]:
    cleaned: list[str] = []
    for tag in tags:
        tag = tag.strip().lower()
        if not tag:
            continue
        if not _TAG.match(tag):
            raise UserError(f"Bad tag '{tag}'. Use letters, numbers, spaces, - or _, up to 30 characters.")
        if tag not in cleaned:
            cleaned.append(tag)
    return cleaned


@tool("writer")
def tag_asset(
    path: Annotated[str, Field(min_length=1, max_length=1000, description="A file path from search_assets, or a folder to tag every indexed file inside it.")],
    tags: Annotated[list[str] | None, Field(max_length=20, description="Tags to add, like ['poster', 'blue', 'gdg'].")] = None,
    client: Annotated[str | None, Field(max_length=60, description="Client to link the file(s) to.")] = None,
) -> str:
    """Add tags and/or a client link to an indexed file, or to every indexed file in a folder.
    This only changes the index. The files themselves are never touched."""
    new_tags = _clean_tags(tags or [])
    new_client = (client or "").strip()
    if not new_tags and not new_client:
        raise UserError("Give at least one tag or a client name.")
    _roots()
    key = _key(path)
    with _db() as conn:
        rows = conn.execute("SELECT path_key, tags FROM assets WHERE path_key = ?", (key,)).fetchall()
        if not rows:
            prefix = key.rstrip(os.sep) + os.sep
            rows = conn.execute(
                "SELECT path_key, tags FROM assets WHERE substr(path_key, 1, length(?)) = ?", (prefix, prefix)
            ).fetchall()
        if not rows:
            raise UserError("That path isn't in the index. Use a path from search_assets, or call reindex first.")
        if len(rows) > MAX_TAG_TARGETS:
            raise UserError(f"That folder has {len(rows)} indexed files. Tag a smaller folder (limit {MAX_TAG_TARGETS}).")
        for row in rows:
            merged = [t for t in row["tags"].split(",") if t]
            for tag in new_tags:
                if tag not in merged:
                    merged.append(tag)
            if new_client:
                conn.execute("UPDATE assets SET tags=?, client=? WHERE path_key=?", (",".join(merged), new_client, row["path_key"]))
            else:
                conn.execute("UPDATE assets SET tags=? WHERE path_key=?", (",".join(merged), row["path_key"]))
    return f"Updated {len(rows)} file(s) in the index."
