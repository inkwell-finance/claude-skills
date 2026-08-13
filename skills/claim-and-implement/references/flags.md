# Flags — full behavior

Moved verbatim from SKILL.md.

- `--dry-run`
  - Skip all Plane writes (no CLAIM, no comments, no state transitions).
  - Skip all `Edit` / `Write` calls to source files.
  - Skip `git commit`.
  - Still run BASELINE + VERIFY gate dry-read (parse outputs without executing if --dry-run is passed to BASELINE? No: gates are read-only by definition, so run them — but don't ACCEPT-gate-retry on failure).
  - Print the full plan of what would happen: claim comment text, edits in dependency order, verification gate output, commit messages, close comment text.
  - Useful for reviewing the plan before committing hours.

- `--resume`
  - Re-run the pre-flight HITL gate before anything else. It is not bypassed by `--resume` the way the state gate is — a `MODE: hitl` marker added mid-flight must stop the resumed run exactly as it would a fresh claim, and a headless resume still refuses if it can't answer.
  - Issue may already be `In Progress` from a prior incomplete run.
  - Re-parse Tier-2 schema.
  - Read `mcp__plane__list_work_item_comments` for the prior claim comment and any scope-creep filings.
  - Inspect `git log` since the branch diverged from main for commits referencing the concern id.
  - Diff against TOUCHES to determine which paths are already addressed.
  - Resume from the earliest incomplete TOUCHES entry. Do NOT re-run CLAIM.
  - Post a resume comment citing prior-run artefacts.

- `--scope-audit-only`
  - Run PRE-FLIGHT + BASELINE + scope-path existence check only.
  - Do NOT CLAIM.
  - Do NOT implement.
  - Do NOT run VERIFY.
  - Output: baseline test result, scope-path drift report, estimated Tier-2 completeness.
  - Useful before committing to a multi-hour claim on a flaky or ambiguous ticket.
