---
name: remediate
description: Recursive gap-analysis-to-fix pipeline for existing code — multi-dimension audit across repos, structured plans/ with dependency graph, batched parallel execution with worktree isolation and inline review, cross-batch audit, calibrate. Scopes — all | <path> | plans/ | plans/<name> | batch N | audit | calibrate. For systemic multi-concern remediation, not single bug fixes, not diff review (/code-review), not building new features (/plan).
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

#### Team composition (complexity-gated)

**For ≤ 4 repos** — use the simple pattern: one Explore agent per repo, each covering all 8 dimensions. Skip to "Per gap" below.

**For 5+ repos** — use the Scout → Analyst → Synthesizer team:

| Round | Role | Model | Count | Input | Output |
|-------|------|-------|-------|-------|--------|
| 1 | **Scouts** | sonnet (low effort) | 1/repo | repo path | Structured findings per dimension: file paths, code snippets, potential issues |
| 2 | **Dimension Analysts** (optional) | sonnet | 1/dimension (up to 8) | All scout outputs for their dimension | Structured gaps for that dimension across ALL repos |
| 3 | **Synthesizer** | fable (fallback: opus) | 1 | All scout/analyst outputs | Cross-cutting summary, deduplication, severity ranking, cross-repo patterns |

**Why teams for large scopes**: Per-repo agents independently assessing security, correctness, etc. miss cross-repo patterns (Run 2's coordinator/index.ts conflict was invisible to individual repo agents). Dimension-oriented analysts see the full picture for their specialty.

**Default — skip dimension analysts**: Sonnet scouts already cover all 8 dimensions with structured output, so Round 2 is optional: go scout → synthesizer directly. Run 13 used this pattern successfully: 8 sonnet scouts → 1 synthesizer, with a 36% dedup rate and no loss of cross-repo pattern detection. Insert dimension analysts only when scout outputs come back unstructured, or when a single dimension spans many repos and needs dedicated cross-repo attention.

**Routing rules:**
- Round 2 analysts receive ALL scout outputs, not just their dimension — context from other dimensions helps (e.g., a security analyst should know about architectural coupling)
- Round 3 synthesizer receives analyst outputs labeled by dimension
- If synthesizer finds contradictions between analysts, it resolves by examining the evidence, not averaging the opinions

**Scope rule — never silently omit a repo**: For an `all` scope, enumerate every repo root in the workspace (excluding vendored/generated trees and external symlinks), present the manifest to the user, and get confirmation — especially repos handling financial state or user data. Run 10 found 3 p0 and 3 p1 issues in a repo (HyPaper) that was excluded from Run 9's scope; a missing repo is a blind spot that compounds across runs. For an explicit single-path scope, analyze only that path — note un-analyzed sibling repos in the summary instead of expanding scope.

#### 8 analysis dimensions
- **Completeness**: stubs, TODOs, unimplemented paths, dead code
- **Correctness**: logic bugs, off-by-one, wrong formulas, wrong assumptions
- **Robustness**: missing error handling, retry, timeout, partial failure
- **Data integrity**: race conditions, lost updates, inconsistent state
- **Security**: secrets exposure, input validation, injection
- **Observability**: missing metrics, logs, alerts for critical paths
- **Testing**: untested critical paths, missing edge cases
- **Architecture**: tight coupling, missing abstractions, scaling bottlenecks

Per gap: **What** → **Where** (file:line) → **Why it matters** → **Adversarial question**

For mathematical expression bugs (off-by-one, wrong direction, wrong sign): **substitute 2-3 concrete values** before declaring the expression is wrong. Run 4 incorrectly "fixed" a drawdown epsilon that was already correct — the analysis said `+ EPSILON` was wrong direction, but evaluating with concrete negative thresholds proved it was right. The revert cost an audit cycle.

Present cross-cutting summary to user (from synthesizer in team mode, or self-synthesized in simple mode).

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
## Resolution   <- appended when STATUS becomes done: date, commit, notes
```

If the repo tracks work externally (td, Plane, etc.), mirror each concern per that repo's convention — e.g., a `PLANE: <id>` pointer line — so the repo's own triage tooling sees the work.

#### Supporting files

Create `plans/CONVENTIONS.md`, `plans/README.md`, and `plans/DEPENDENCIES.md` — full content specs for all three are in [references/plans-scaffold.md](references/plans-scaffold.md).

#### Model assignment

**By implementation complexity (for implementer agents):**
| Tag | Model | Use when |
|-----|-------|----------|
| `mechanical` | sonnet (low effort) | Clear pattern, schema fix, config, single-file edit with < 10 files to read |
| `architectural` | sonnet | System interactions, failure modes, cross-repo, or mechanical tasks needing 10+ file reads |
| `research` | fable (fallback: opus) | Critical design decisions requiring deep reasoning about tradeoffs |

**By team role (for non-implementer agents):**
| Role | Model | Rationale |
|------|-------|-----------|
| Scout | sonnet (low effort) | Broad data gathering with structured output |
| Dimension Analyst | sonnet | Structured analysis within one domain |
| Synthesizer | fable (fallback: opus) | Cross-referencing, resolving contradictions, severity ranking |
| Reviewer | fable (fallback: opus) | Judgment on correctness, completeness, and downstream implications |
| Blocker Verifier | sonnet (low effort) | Simple existence/state checks |

Never assign haiku to any role — it is below the reliability bar here. When a mechanical concern's spec is fully self-contained (no live-state interrogation needed), routing it through the codex wrapper (`gpt-5.6-luna`/`-terra`) per the user's model-routing table is a valid cost play; otherwise default to sonnet.

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

Before the first batch, record each affected repo's baseline in `plans/<plan-name>/EXECUTION-LOG.md`: repo root, branch, HEAD SHA, and `git status --porcelain` output (pre-existing dirty/untracked files). All later diffs are taken per-repo against this baseline — one `git diff` cannot span multiple repos, and without a baseline, pre-existing user changes get misattributed to agents.

#### Batch formation
1. **BATCH -1 — STATUS VERIFICATION**: Before regression checks, launch sonnet (low effort) agents to verify each "open" concern is actually open in source. Run 3 found 42% of "open" concerns were already fixed with stale STATUS. This pass avoids wasting execution agents on no-ops. Each agent runs the concern's `## Verify` procedure (checking every TOUCHES file, not just one) and reports DONE / PARTIAL / NOT_DONE with file:line evidence. Only evidence-backed DONE closes a concern; PARTIAL stays open with a note on what remains.
2. **BATCH 0 — REGRESSION CHECK**: If prior-run reconciliation flagged potential regressions (done items that fresh analysis questions), launch read-only sonnet (low effort) verification agents FIRST. Each reads the specific file and reports FIXED / NOT_FIXED. Results determine which items need new concerns vs can be closed. Do not skip this — Run 2 found 6 of 7 regression checks were NOT_FIXED.
3. Start with zero-blocker tasks
4. Model by COMPLEXITY tag (see mapping above)
5. **SAME-FILE RULE**: Tasks whose TOUCHES overlap MUST be in the same agent or sequential batches
6. **CROSS-REPO ATOMIC RULE**: When a concern changes a protocol type (required field, new field, removed field), ALL repos consuming that type must be updated in the same agent or batch. This includes test files.
7. **HIGH-TRAFFIC FILE RULE**: If 3+ concerns touch the same file (e.g., a service's index.ts), strongly prefer a SINGLE agent for all of them. Run 2's audit found 5 of 8 issues originated from multi-agent edits to coordinator/index.ts.
8. **SHARED-TYPE FIELD RULE**: When a concern adds a required field to a shared type (e.g., protocol's `BacktestResult`), the same agent (or batch) must also update ALL constructors of that type across all repos. Run 4's audit found a new `winRate` field added to the type but missing from the sandbox constructor — broke all job submissions.
9. Max 10 agents per batch
10. **OPTIONAL-FIRST RULE**: When adding a field to a schema/type consumed by multiple repos, make it `.optional()` initially. Only make it required after ALL producers are updated to include it. Run 13 added a required `signature` field to a protocol schema — the coordinator's broadcast function didn't include it, silently breaking all downstream consumers. Pattern: add as optional → update all producers → flip to required — and the flip MUST happen in the same run. Never close a plan with a security-relevant field (signature, auth, permission) still optional; if temporary absence would weaken an invariant, update all producers and consumers atomically in one agent instead (see CROSS-REPO ATOMIC RULE).
11. **SEMANTIC VERIFICATION RULE**: Agents must verify the semantic meaning of operations, not just mechanical correctness. When incrementing a counter or modifying a field, ask: "does this operation belong in this instruction/function?" Run 13 found `proposals_accepted` correctly incremented with checked arithmetic inside `submit_proposal` — but submission ≠ acceptance, so the increment was semantically wrong despite being mechanically sound.

#### Isolation (mandatory for parallel batches)
TOUCHES analysis *predicts* conflicts; isolation *enforces* them away — TOUCHES lists are guesses made before the code was read. For any batch with more than one implementer:
- Give each implementer `isolation: 'worktree'`. Each agent commits only inside its own worktree; the orchestrator reviews each isolated diff, merges the batch branches sequentially in dependency order, and reruns verification on the merged state.
- If worktree isolation is unavailable, serialize the implementers — never run two write-capable agents in the same working tree.

Single-agent batches may edit in place, leaving changes uncommitted for the orchestrator.

#### Pre-batch blocker verification
Before each batch, launch sonnet (low effort) agents to verify each BLOCKED_BY claim using its VERIFY_BLOCKER check. False blockers get promoted into the current batch.

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

Use the per-agent prompt template in [references/agent-prompts.md](references/agent-prompts.md).

#### Inline review (per batch)

After each batch of implementers completes, run a **fable reviewer** (fallback: opus) before advancing to the next batch.

| Step | Role | Model | Input | Output |
|------|------|-------|-------|--------|
| 1 | **Reviewer** | fable (fallback: opus) | All diffs from this batch + their concern files + PRIOR CHANGES context | Pass/fail per agent + issues list with severity |
| 2 | **Fixer** | sonnet (or per-complexity) | Reviewer's issues list | Targeted fixes for failed items |

**Reviewer prompt template:** use the reviewer prompt template in [references/agent-prompts.md](references/agent-prompts.md).

**When to skip inline review:**
- Batch contains only mechanical fixes (< 3 files each, no shared types)
- Batch is a status verification or regression check (BATCH -1/0)

**Why this matters:** Run 2's 5/8 audit issues and Run 4's missing winRate propagation would have been caught here instead of in the post-hoc audit, saving a full loop cycle.

#### After each batch (post-review)
- Update todos
- Classify each agent result SUCCESS / PARTIAL / FAILED. For PARTIAL or FAILED: preserve the diff, then either retry once with a narrowed prompt or fold the remainder into the fixer round. Never mark a concern done without verification evidence.
- Append to `plans/<plan-name>/EXECUTION-LOG.md` under a `## Batch N` heading: the scorecard (concern id, model, time, result, review pass/fail) and the shared-file changelog the next batch's PRIOR CHANGES context is built from
- After inline review passes, merge worktree branches (or commit in-place edits) using the repo's commit format, gated on the user's batch approval; record commit hashes in each concern's Resolution
- Check: did this batch unblock new tasks?

**Gate**: User approves next batch (or "keep going" for autonomous).

---

### Phase 4: AUDIT

**Mandatory.** After all execution batches complete. With inline review catching per-batch issues, this phase focuses on **cross-batch consistency** — problems that only become visible when viewing all changes together.

#### 4a: Self-check
- For each affected package/repo, run its declared verification gate — from its CLAUDE.md, CI config, or package scripts (typecheck, build, tests, custom validators). Fall back to the toolchain default (`tsc --noEmit`, `cargo check` + `cargo test`, ...) only when no gate is declared.
- Record each command and its exit status. Treat unavailable required tooling as UNVERIFIED, never as passed.
- Check added diff lines (not the whole tree) for newly introduced `TODO`, `FIXME`, `HACK`.

#### 4b: Cross-batch consistency review
Launch a **fable audit agent** (fallback: opus) with per-repo diffs taken against the baselines recorded in EXECUTION-LOG.md — including newly untracked files and worktree-branch commits — aggregated into one manifest covering ALL batches. One `git diff` cannot span multiple repos; the aggregate manifest is the whole picture. This is the highest-value use of the judgment tier: reasoning about systemic consistency across many changes.

Check for the failure patterns catalogued in `references/audit-checklist.md` (in this skill's directory). Read that file and paste its full checklist into the audit agent's prompt — it covers multi-agent conflicts, incomplete wiring, protocol/type drift, SQL mismatches, security, cross-repo consistency, identity-key confusion, metrics double-counting, dead imports, duplicate timers, async call-site drift, required-field propagation, replacement-method wiring, schema optionality drift, and auditor trace depth.

Also run `/blind-review` in parallel — and do not give it this checklist.

#### 4c: Decision
- Minor (< 5 mechanical) → fix inline
- Significant → new plan, loop to Phase 2
- Conflicts on shared files → single agent that reads ALL changes

**Gate**: User decides: close, fix, or loop.

---

### Phase 5: CLOSE

- Update plan files: STATUS, Resolution notes
- Update README with stats
- Append to `plans/CALIBRATION.md` HISTORY section. If the file doesn't exist, create it with two sections: `## RULES` (one imperative bullet per project-specific rule, suffixed with its source run and, once calibrated, `[baked into skill YYYY-MM-DD]`) and `## HISTORY` (one `### Run N` block per run: date, scope, concerns done/open, surprises, false positives)
- **Ask the user**: "Run `/remediate calibrate` to bake learnings into the skill?"

---

## Calibrate

**Scope**: `/remediate calibrate`

This command reads `plans/CALIBRATION.md` and **rewrites sections of this skill file** based on the learnings. Full procedure, filter rules, and skill-vs-CALIBRATION.md boundaries: [references/calibrate.md](references/calibrate.md).

---

## Scope Interpretation

| Input | Behavior |
|-------|----------|
| `all` | Full pipeline: analyze all repos |
| `repos/<name>` or `<path>` | Analyze single repo or directory |
| `plans/` | Skip Phase 1-2, execute existing plans |
| `plans/security-auth` | Execute single plan |
| `batch 3` | Resume: read DEPENDENCIES.md's Batch Plan + EXECUTION-LOG.md, verify batches < N are logged complete, rebuild PRIOR CHANGES from the changelog sections. Reject the scope if EXECUTION-LOG.md is missing or incompatible |
| `audit` | Skip to Phase 4, diffing against EXECUTION-LOG.md baselines; if none exist, ask the user for an explicit base ref |
| `calibrate` | Read CALIBRATION.md and rewrite this skill |
