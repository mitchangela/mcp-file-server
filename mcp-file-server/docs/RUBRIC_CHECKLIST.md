# Rubric map: where each point comes from

Rubric: 100 points. "Built" means the scaffold already has it. "You" means it only counts once
you do it and have the evidence.

| Criterion | Pts | Built | Still on you |
|---|---|---|---|
| A. Agent efficiency | 20 | Paged reads, capped search and diff, `read_state` in one call, read-before-write enforced, `INSTRUCTIONS` tell agents to plan first | Run the demo, keep the transcript honest, show few purposeful calls, note any retries |
| B. Agent and tool management | 20 | Roles, gated delete, audit log, four handoff files, `append_handoff` | Use the handoff across 2+ sessions. Keep PROJECT_STATE fresh. Export the logs |
| C. Tool design | 20 | 12 tools, strict schemas, `isError` messages | Run Inspector, screenshot, run against a real client |
| D. Stack and architecture | 15 | Separated modules, secrets in `.env`, pm2 config, stateless HTTP | Write the justification, prove it survives a restart |
| E. Security and sandboxing | 10 | Sandbox, traversal tests, token auth, gated delete, Host check | Run the tests, check the live endpoint rejects no-token, write the threat notes |
| F. Docs, practice, demo | 15 | README, templates, smoke test | Verify the README from scratch, meaningful git log, practise the demo and Q&A |

## Evidence to submit (from the brief)

- [ ] Repository link and README
- [ ] Transcript of one multi-step task (`docs/TRANSCRIPT_TEMPLATE.md`)
- [ ] PLAN_LOG and CHECKPOINT files (`evidence/`)
- [ ] 5-minute live demo
- [ ] Short report (`docs/REPORT_TEMPLATE.md`)

## Likely Q&A questions

- Why does `write_file` refuse to overwrite without a version?
- How does the sandbox stop a symlink escape?
- Why are the tools split into reader/writer/admin?
- What happens if two agents edit the same file?
- Why stateless HTTP?
- What is the weakest part of your security?
