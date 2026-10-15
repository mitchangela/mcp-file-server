# Tool-call transcript: demo task

Task: (one line)
Date and client used: (for example Claude, custom connector, Oct __ 2026)
Sessions: (how many, and which role each used)

Paste the real chat transcript under each session. Then fill the summary table from
`evidence/tool_calls.jsonl`.

## Session 1: Builder (writer)

(paste transcript)

## Session 2: Finisher (writer)

(paste transcript)

## Session 3: Reviewer (reader)

(paste transcript)

## Call summary

| # | Session | Tool | Why this call | Result |
|---|---|---|---|---|
| 1 | 1 | read_state | Load context | OK |
| | | | | |

Totals: ___ calls, ___ errors, ___ retries.

## Efficiency notes

- Did every write follow a read? (yes/no, and any exception)
- Calls that were wasted, and what you changed because of them
- How each session ended (stop condition)

## Errors on purpose

| Attempt | Error returned |
|---|---|
| Overwrite without if_version | |
| Delete without confirm | |
| Path escape | |
| Reader token tries to write | |
