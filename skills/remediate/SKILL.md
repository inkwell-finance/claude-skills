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

#### Prior-run reconciliation

Before moving to Phase 2, check if prior plans exist (any `plans/` directory in the workspace or its repos). If they do:

1. Read the prior `README.md` to understand what was attempted
2. Read each concern file's STATUS — categorize as done, open, or blocked
3. If a `CALIBRATION.md` exists, read it for rules and history
4. Map fresh analysis findings against prior work:
   - **Duplicate of open item** → carry forward the existing plan (it has execution context)
   - **Covered by done item** → flag as potential regression for verification
   - **Genuinely new** → create new concern
5. Present the reconciliation to the user: what's carried forward, what's new, what needs regression verification

This ensures fresh analysis catches real issues without re-planning already-scoped work.

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

##### `plans/CONVENTIONS.md`

Must contain all of the following sections:

1. **File Format** — the full concern file template (STATUS, PRIORITY, REPOS, COMPLEXITY, TOUCHES, Problem, Evidence, Fix, Cross-Repo Side Effects, Verify, Resolution)
2. **COMPLEXITY Field** — table mapping mechanical/architectural/research to meaning and model assignment
3. **Plan Lifecycle** — state machine: `open → in-progress → done | blocked`. Instructions for starting work (set status, check DEPENDENCIES.md), completing work (set status, add Resolution section, do NOT delete the file), and handling blocks (set status, add BLOCKED_BY)
4. **Resolution Format** — when STATUS becomes done, append: Completed date, PR/Commit link, Notes (anything surprising or learned)
5. **Plan Structure** — each plan directory has `00-overview.md` (scope table, local deps, external deps, remediation order) plus numbered concern files
6. **Cross-Plan Dependencies** — how `00-overview.md` owns local deps while `DEPENDENCIES.md` maps cross-plan edges
7. **Learning From Completed Plans** — Resolution notes capture underestimates, overestimates, missed dependencies, wrong assumptions, and techniques that worked. Future analyses read these notes to calibrate severity, identify surprise-prone repos, and improve verification steps.

##### `plans/README.md`

Must contain:

1. **Context line** — date, what was analyzed, relationship to prior runs if any
2. **Plans table** — columns: #, Plan (linked), Concerns count, p0/p1/p2 counts, Status, Completed date
3. **Batch Execution Order** — reference to DEPENDENCIES.md plus summary table (batch #, what plans/concerns, est. agents, model mix)
4. **Execution Stats** (added during/after execution) — total concerns, agents by model, open items remaining
5. **Calibration reference** — pointer to CALIBRATION.md if it exists
6. **Adding a New Plan** — instructions: create dir, write 00-overview.md, write concern files, add to table, add edges to DEPENDENCIES.md

##### `plans/DEPENDENCIES.md`

Must contain:

1. **Repo Dependency Graph** — ASCII diagram showing which repos import from which (protocol → trader/coordinator/researcher, contracts → researcher/coordinator, etc.)
2. **Change Impact Matrix** — table with columns: Plan/Concern, Primary Repo, Must Also Change, Regression Risk. One row per concern that has cross-repo side effects. Include specific risk description (e.g., "if coordinator enforces sigs before researcher signs → all proposals rejected")
3. **Atomic Groups** — list of concern sets that MUST ship together or in strict sequence. Explain why (shared file, protocol type change, etc.)
4. **Sequential Constraints** — ordered pairs where A must complete before B, with rationale
5. **Parallel-Safe** — list of concerns/plans that are safe to run independently
6. **Batch Plan** — table: batch #, plans/concerns included, agent count, model assignment, rationale for grouping

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
1. **BATCH 0 — REGRESSION CHECK**: If prior-run reconciliation flagged potential regressions (done items that fresh analysis questions), launch read-only haiku verification agents FIRST. Each reads the specific file and reports FIXED / NOT_FIXED. Results determine which items need new concerns vs can be closed. Do not skip this — Run 2 found 6 of 7 regression checks were NOT_FIXED.
2. Start with zero-blocker tasks
3. Model by COMPLEXITY tag (see mapping above)
4. **SAME-FILE RULE**: Tasks whose TOUCHES overlap MUST be in the same agent or sequential batches
5. **CROSS-REPO ATOMIC RULE**: When a concern changes a protocol type (required field, new field, removed field), ALL repos consuming that type must be updated in the same agent or batch. This includes test files.
6. **HIGH-TRAFFIC FILE RULE**: If 3+ concerns touch the same file (e.g., a service's index.ts), strongly prefer a SINGLE agent for all of them. Run 2's audit found 5 of 8 issues originated from multi-agent edits to coordinator/index.ts.
7. Max 10 agents per batch

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
- If you track entities by identity key (user, researcher, node), use ONE consistent key type everywhere (e.g., pubkey). Do NOT mix peerId, pubkey, and proposalId — this silently breaks lookups across components.
- If you emit a metric (counter.inc, histogram.observe), verify it fires only on actual state transitions, not intermediate events. A 3-node redundancy job must only inc(finalized) once, not on each partial result.
- If you pass a snapshot/value to an adapter or downstream consumer, verify the consumer actually reads it. Pattern to avoid: caller passes PnLSnapshot, adapter ignores it and re-reads live state.
- If you add a periodic timer/sweep (setInterval), grep the codebase first for existing timers on the same resource. Two sweeps on the same queue create races.
- If you track child process PIDs for shutdown, register the PID BEFORE the async work completes — not after. A PID registered after the process exits is useless or dangerous (PID recycling).
- `side === 'sell'` is NOT a reliable proxy for "close order" — only `reduceOnly` is
- `as any` casts on proto/gRPC types hide silent failures — flag these and avoid adding new ones
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

**Identity key confusion**: components using different keys for the same entity (pubkey vs peerId vs proposalId). Check that Maps, lookups, and stores all use the same key type for a given entity.

**Metrics double-counting**: metrics incremented on intermediate events (every partial result) instead of only on state transitions (actual finalization). Check that counters inside loops or callback handlers fire at the right granularity.

**Dead imports**: one agent imports a metric/function, another agent moves the actual usage to a different file. Grep for unused imports in modified files.

**Duplicate timers/sweeps**: two agents both add setInterval for the same resource (e.g., queue processing). Check for multiple timers targeting the same Redis key or data structure.

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
