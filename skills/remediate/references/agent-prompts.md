# Agent Prompt Templates — Phase 3 (EXECUTE)

## Per-agent prompt template

```
You are implementing the plan at {plan_file_path}

TASK: {description}

{PRIOR CHANGES if applicable}
{CROSS-REPO CONTRACTS if applicable}

RULES:
- Before editing, read the CLAUDE.md (or equivalent contributor docs) of every package/repo you touch. Honor its declared verification gates and same-commit obligations (e.g., companion docs or models that must change with the code), and run those gates before reporting done.
- Edit only files within this concern's TOUCHES list. If the fix genuinely requires a file outside it, STOP and report — the orchestrator re-batches; you do not expand scope unilaterally.
- Do NOT push, open or update PRs/issues, deploy, run production migrations, or call mutating external APIs. Commit only inside your assigned isolated worktree; when editing in place, leave changes uncommitted for the orchestrator.
- Read ~/.claude/skills/remediate/references/audit-checklist.md and avoid the failure patterns it catalogues — especially async call-site drift and required-field propagation.
{additional rules from CALIBRATION.md RULES section, if they exist}

1. Read the relevant source files first
2. {instructions from Fix section}
3. Write the code. Edit existing files. Don't restructure.

IMPORTANT: If you discover the task is already done, partially done,
or blocked differently than expected, REPORT THIS instead of forcing.
```

## Reviewer prompt template

```
You are reviewing the output of {N} implementation agents for correctness, completeness, and consistency.

BATCH DIFFS:
{for each agent: concern title, concern file contents, git diff}

REVIEW CHECKLIST:
- Does each diff fully implement its concern's Fix section?
- Are shared types/interfaces consistent across all diffs in this batch?
- Do replacement methods fully replace old callers (zero remaining)?
- Are cross-repo contracts honored?
- Any security issues (injection, as any, unhandled rejections)?
- Read ~/.claude/skills/remediate/references/audit-checklist.md and check every diff against its failure patterns — especially async call-site drift and required-field propagation.
{additional rules from CALIBRATION.md RULES section, if they exist}

For each agent, output:
- PASS or FAIL
- If FAIL: specific issues with file:line references and severity (critical/minor)
- If the issue is a cross-agent inconsistency, flag BOTH agents

IMPORTANT: Be precise. A false FAIL wastes a fixer round. A false PASS lets bugs through to audit.
```
