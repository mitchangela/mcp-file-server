"""All tools. server.py registers everything listed in ALL_TOOLS."""
from tools.files import delete_file, list_files, read_file, str_replace, write_file
from tools.git_tools import git_commit, git_diff, git_log, git_status
from tools.handoff import append_handoff, read_state
from tools.search import search_code

ALL_TOOLS = [
    list_files,
    read_file,
    write_file,
    str_replace,
    delete_file,
    search_code,
    git_status,
    git_diff,
    git_commit,
    git_log,
    read_state,
    append_handoff,
]

DESTRUCTIVE = {"delete_file"}
READ_ONLY = {
    "list_files", "read_file", "search_code", "git_status",
    "git_diff", "git_log", "read_state",
}
