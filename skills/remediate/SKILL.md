---
name: remediate
description: Run gap analysis across repos, generate structured remediation plans, and execute fixes in parallel batches with model-appropriate task assignment. Use when the user wants to audit, analyze, or fix issues across a codebase.
argument-hint: "[scope]"
disable-model-invocation: true
---

# Remediate

Run a recursive gap-analysis-to-fix pipeline. Scope can be a repo path, a plan directory, "all", or "calibrate".

## Phases

Execute in order. Ask the user before advancing phases.

```
ANALYZE → PLAN → EXECUTE → AUDIT → (loop if issues found) → CLOSE
```

If scope is `calibrate`, skip to the Calibrate section at the bottom.

---

### Phase 1: ANALYZE

Launch one Explore agent per repo in parallel.

Each agent identifies gaps across 8 dimensions:
- **Completeness**: stubs, TODOs, unimplemented paths, dead code
- **Correctness**: logic bugs, off-by-one, wrong formulas, wrong assumptions
- **Robustness**: missing error handling, retry, timeout, partial failure
- **Data integrity**: race conditions, lost updates, inconsistent state
- **Security**: secrets exposure, input validation, injection
- **Observability**: missing metrics, logs, alerts for critical paths
- **Testing**: untested critical paths, missing edge cases
- **Architecture**: tight coupling, missing abstractions, scaling bottlenecks

Per gap: **What** → **Where** (file:line) → **Why it matters** → **Adversarial question**

Synthesize into cross-cutting summary. Present to user.

**Gate**: User confirms before Phase 2.

---

### Phase 2: PLAN

Create plans at `plans/<plan-name>/` grouped by cross-cutting theme.

#### Concern file format
```markdown
# Title
STATUS: open
PRIORITY: p0 | p1 | p2
REPOS: affected repos
COMPLEXITY: mechanical | architectural | research
TOUCHES: list of file paths this fix will modify

## Problem
## Evidence
## Fix
## Cross-Repo Side Effects
## Verify
```

#### Supporting files
- `plans/README.md` — index
- `plans/DEPENDENCIES.md` — cross-plan graph (atomic groups, sequential, parallel-safe)
- `plans/CONVENTIONS.md` — lifecycle, tags, resolution format

#### COMPLEXITY → model mapping
| Tag | Model | Use when |
|-----|-------|----------|
| `mechanical` | haiku | Clear pattern, schema fix, config, single-file edit with < 10 files to read |
| `architectural` | sonnet | System interactions, failure modes, cross-repo, or mechanical tasks needing 10+ file reads |
| `research` | opus | Only the single most critical design decision per run. Most "research" is actually architectural — use sonnet. |

#### Dependency rules
Each `00-overview.md` has:
- Scope table
- External dependencies with BLOCKED_BY + VERIFY_BLOCKER
- Remediation order with COMPLEXITY column

**CRITICAL**: Every BLOCKED_BY must include a VERIFY_BLOCKER — a concrete check (file exists? function exists? endpoint returns data?) that an agent can run in < 30s to confirm the blocker is real.

**Gate**: User confirms plan structure and batch order.

---

### Phase 3: EXECUTE

Launch batched parallel agents with model overrides.

#### Batch formation
1. Start with zero-blocker tasks
2. Model by COMPLEXITY tag (see mapping above)
3. **SAME-FILE RULE**: Tasks whose TOUCHES overlap MUST be in the same agent or sequential batches
4. **CROSS-REPO ATOMIC RULE**: When a concern changes a protocol type (required field, new field, removed field), ALL repos consuming that type must be updated in the same agent or batch. This includes test files.
5. Max 10 agents per batch

#### Pre-batch blocker verification
Before each batch, launch haiku agents to verify each BLOCKED_BY claim using its VERIFY_BLOCKER check. False blockers get promoted into the current batch.

#### Context propagation
When an agent edits a file that was modified in a previous batch, its prompt MUST include:
```
PRIOR CHANGES TO THIS FILE:
- {file}: {what was added/changed} for {why}. New imports: X. New functions: Y. New fields: Z.
```

When an agent implements against a cross-repo interface, its prompt MUST include:
```
CROSS-REPO CONTRACT:
- {repo}.{function}({params}) expects {shape}
- {type} in {repo} requires fields: {list}
```

#### Per-agent prompt template
```
You are implementing the plan at {plan_file_path}

TASK: {description}

{PRIOR CHANGES if applicable}
{CROSS-REPO CONTRACTS if applicable}

RULES:
- If you use SQL DDL + application queries, verify the queries don't assume constraints/indexes the DDL didn't create
- If you instantiate a component, verify it's wired to its consumer AND cleaned up in shutdown
- If you modify a shared type/interface, all downstream consumers (including tests) must be updated to match
- If you embed dynamic values in code strings, sanitize them (e.g., JSON.stringify) before interpolation
{additional rules from CALIBRATION.md RULES section, if they exist}

1. Read the relevant source files first
2. {instructions from Fix section}
3. Write the code. Edit existing files. Don't restructure.

IMPORTANT: If you discover the task is already done, partially done,
or blocked differently than expected, REPORT THIS instead of forcing.
```

#### After each batch
- Update todos
- Scorecard (task, model, time, result)
- Build shared-file changelog for next batch's context propagation
- Check: did this batch unblock new tasks?

**Gate**: User approves next batch (or "keep going" for autonomous).

---

### Phase 4: AUDIT

**Mandatory.** After all execution batches complete:

#### 4a: Self-check
- `tsc --noEmit` across affected repos
- Run existing test suites
- Grep for `TODO`, `FIXME`, `HACK` introduced by agents

#### 4b: Re-analyze changed files
Launch audit agents per repo, scoped to `git diff --name-only`. Check for:

**Multi-agent conflicts**: fields added but not used by another agent, duplicate definitions, inconsistent imports

**Incomplete wiring**: `new X()` not passed to consumer, async methods with sync call sites, modules created but not imported

**Protocol/type drift**: test files using old type shapes, validation schemas out of sync with interfaces, IDL/proto field name mismatches with application code

**SQL mismatches**: application code assuming constraints migrations didn't create, missing indexes for query patterns

**Security**: template injection, `as any` casts, non-null assertions on optional fields, unhandled promise rejections

**Cross-repo consistency**: canonicalization functions producing different output, signing/verification algorithm mismatches

#### 4c: Decision
- Minor (< 5 mechanical) → fix inline
- Significant → new plan, loop to Phase 2
- Conflicts on shared files → single agent that reads ALL changes

**Gate**: User decides: close, fix, or loop.

---

### Phase 5: CLOSE

- Update plan files: STATUS, Resolution notes
- Update README with stats
- Append to `plans/CALIBRATION.md` HISTORY section
- **Ask the user**: "Run `/remediate calibrate` to bake learnings into the skill?"

---

## Calibrate

**Scope**: `/remediate calibrate`

This command reads `plans/CALIBRATION.md` and **rewrites sections of this skill file** based on the learnings.

Steps:
1. Read `plans/CALIBRATION.md` — extract the RULES section and HISTORY section
2. Read this skill file (`${CLAUDE_SKILL_DIR}/SKILL.md`)
3. For each RULE, determine which section of the skill it applies to:
   - Model mapping rules → update the COMPLEXITY table
   - Batch formation rules → update batch formation section
   - Agent prompt rules → update the RULES block in the prompt template
   - Audit checklist rules → update the 4b checklist
   - Security rules → add to prompt template RULES block
4. For each HISTORY entry's "key learnings", check if they're already reflected in the skill. If not, add them to the appropriate section.
5. Present the diff to the user for approval before writing.

**What this means**: The skill evolves. Run 1 discovers that agents don't check SQL constraints → that becomes a rule → `calibrate` adds it to the prompt template → Run 2 agents always check SQL constraints. The skill file is the single source of truth, not a separate calibration file that might be forgotten.

After calibration, CALIBRATION.md's RULES section can note "baked into skill on YYYY-MM-DD" for each rule that was applied, so future runs don't re-apply the same rule.

---

## Scope Interpretation

| Input | Behavior |
|-------|----------|
| `all` | Full pipeline: analyze all repos |
| `repos/<name>` or `<path>` | Analyze single repo or directory |
| `plans/` | Skip Phase 1-2, execute existing plans |
| `plans/security-auth` | Execute single plan |
| `batch 3` | Resume from specific batch |
| `audit` | Skip to Phase 4 on recent changes |
| `calibrate` | Read CALIBRATION.md and rewrite this skill |

## Key Behaviors

- **Never guess file contents** — always read before editing
- **Preserve existing patterns** — match codebase style
- **Track progress** — TodoWrite for batch tracking
- **Report as agents complete** — don't wait for all
- **Verify blockers at execution time** — don't trust the plan blindly
- **Propagate context between batches** — agents must know what previous agents did
- **Include cross-repo contracts in prompts** — agents must know the interface they implement against
- **Agents report anomalies** — don't force, report
