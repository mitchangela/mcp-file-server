# Demo task: build a one-page portfolio site

Multi-step, spans three sessions, touches every handoff file. Use your own wording if you like.
Start each session as a NEW chat so nothing carries over except the files.

## Roles

| Session | Role | Token | Job |
|---|---|---|---|
| 1 Builder | writer | writer token | Plan and build the first half |
| 2 Finisher | writer | writer token (new chat, or your second Claude account) | Finish and commit |
| 3 Reviewer | reader | reader token | Check the work, change nothing |

Free plan = one custom connector per account. To switch roles, edit the connector URL
(secret-path form with the other token), or use your second account for the second role.

## Session 1: Builder

> Use the file server. First call read_state. Then write a 5-step plan to PLAN_LOG for a one-page
> portfolio site for a freelance graphic designer in site/ (index.html, style.css). Do steps 1 to 3
> only: HTML structure, CSS, sample content. Then update PROJECT_STATE, add a CHECKPOINT with what
> state the files are in, commit, and stop.

Expected calls: `read_state`, `append_handoff` (PLAN_LOG), `write_file` x2-3, `str_replace` as needed,
`append_handoff` (CHECKPOINTS), `str_replace` (PROJECT_STATE), `git_commit`.

## Session 2: Finisher (new chat)

> Continue the project. Call read_state and follow the latest CHECKPOINT. Finish steps 4 and 5:
> responsive layout and a short site/README.md. Log any choice you make in DECISIONS. Update
> PROJECT_STATE, add a CHECKPOINT, commit.

What to look for: it should not ask you what the project is. It should read, search or read
parts of files, edit with `str_replace`, and commit.

## Session 3: Reviewer (new chat, reader token)

> Call read_state. Review site/ against the plan in PLAN_LOG. List anything missing or wrong.
> Do not change anything.

This shows role separation: if it tries to write, it gets a clear error. Try asking it to
write on purpose, and keep that error as evidence.

## Keep for evidence

- The chat transcript of all three sessions
- `evidence/` from `scripts/export_evidence.py`
- A short note on any retries or wasted calls and why (the rubric rewards few, purposeful calls)
