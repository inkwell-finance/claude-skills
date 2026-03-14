---
name: plan
description: Decompose a feature, migration, or initiative into structured plans with dependency graphs and batched parallel execution. Use when the user describes something they want to BUILD (not fix).
argument-hint: "<goal>"
disable-model-invocation: true
---

# Plan

Decompose a goal into structured, executable plans. Then optionally execute them.

Unlike `/remediate` (reactive — find what's broken, fix it), `/plan` is proactive — the user has a goal, this skill decomposes it into work.

```
EXPLORE → DESIGN → DECOMPOSE → (optional) EXECUTE → AUDIT → CLOSE
```

---

### Phase 1: EXPLORE

Understand what exists before deciding what to build.

Launch Explore agents to map the relevant parts of the codebase:
- What components/modules already exist that relate to the goal?
- What patterns does the codebase use? (frameworks, logging, testing, config)
- What interfaces/contracts exist between components?
- What would need to change vs what needs to be created from scratch?

Output: a **landscape summary** — what exists, what's relevant, what the goal needs from the codebase.

**Gate**: Present landscape to user. Confirm understanding of the goal before designing.

---

### Phase 2: DESIGN

Make architectural decisions before writing concern files.

For non-trivial goals, launch a Plan agent (opus or sonnet) to:
- Identify the key design decisions (technology choices, patterns, data flow)
- Propose 2-3 approaches with tradeoffs
- Identify risks and unknowns
- Recommend an approach

For simple goals, skip this phase — go straight to DECOMPOSE.

Output: a **design brief** — approach chosen, key decisions made, risks identified.

Write to `plans/<goal-name>/DESIGN.md`:
```markdown
# Design: <goal>

## Approach
## Key Decisions
| Decision | Choice | Alternatives considered | Rationale |
## Risks
## Open Questions (if any — resolve before DECOMPOSE)
```

**Gate**: User approves design before decomposition. Open questions must be resolved.

---

### Phase 3: DECOMPOSE

Break the design into executable concern files. Same structure as `/remediate` plans.

#### Plan directory
```
plans/<goal-name>/
├── DESIGN.md              # From Phase 2
├── 00-overview.md          # Scope, deps, remediation order
├── 01-concern.md           # First task
├── 02-concern.md           # Second task
└── ...
```

#### Concern file format
```markdown
# Title
STATUS: open
PRIORITY: p0 | p1 | p2
REPOS: affected repos
COMPLEXITY: mechanical | architectural | research
TOUCHES: list of file paths this will create or modify

## Goal
What this concern achieves (not what's broken — what's being built).

## Approach
How to implement it. Code samples for non-obvious parts.

## Cross-Repo Side Effects
What changes in other repos as a result.

## Verify
How to confirm this works.
```

#### COMPLEXITY → model mapping
| Tag | Model | Use when |
|-----|-------|----------|
| `mechanical` | haiku | Clear implementation, schema, config, boilerplate, < 10 files |
| `architectural` | sonnet | System integration, cross-repo, new abstractions, 10+ files |
| `research` | opus | Only for the single most critical design decision. Rare. |

#### Dependency graph
Create `00-overview.md` with:
- Scope table (all concerns with COMPLEXITY and TOUCHES)
- BLOCKED_BY + VERIFY_BLOCKER for each dependency
- Batch order (which concerns can parallelize)
- Estimated total batches

Every BLOCKED_BY must have a VERIFY_BLOCKER — a concrete 30s check to confirm the blocker is real at execution time.

#### Shared-file analysis
Before finalizing the plan, check: do any concerns have overlapping TOUCHES? If so:
- Combine into a single concern, OR
- Mark as sequential with explicit ordering, OR
- Note which agent gets priority and what context the later agent needs

**Gate**: Present the decomposition to user. Confirm concern list, batch order, and complexity assignments.

---

### Phase 4: EXECUTE (optional)

User can say "execute" or "just plan" (skip to CLOSE).

If executing, follow the same rules as `/remediate` Phase 3:

#### Batch formation
1. Zero-blocker tasks first
2. Model by COMPLEXITY tag
3. **SAME-FILE RULE**: overlapping TOUCHES → same agent or sequential
4. **CROSS-REPO ATOMIC RULE**: shared type changes → same agent/batch for all consumers
5. Max 10 agents per batch

#### Pre-batch blocker verification
Before each batch, verify BLOCKED_BY claims are still real.

#### Context propagation
Later agents get PRIOR CHANGES summaries for shared files.
Cross-repo agents get CONTRACT specifications.

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
- If you embed dynamic values in code strings, sanitize them before interpolation
{additional rules from CALIBRATION.md if it exists}

1. Read the relevant source files first
2. {instructions from Approach section}
3. Write the code. Edit existing files where possible. Create new files only when necessary.

IMPORTANT: If you discover the task is already done, partially done,
or blocked differently than expected, REPORT THIS instead of forcing.
```

#### After each batch
- TodoWrite progress update
- Scorecard (task, model, time, result)
- Shared-file changelog for next batch
- Unblocked task check

**Gate**: User approves each batch (or "keep going" for autonomous).

---

### Phase 5: AUDIT

If Phase 4 was executed, audit is **mandatory**. Same as `/remediate`:

#### 5a: Self-check
- Type check / lint / build across affected repos
- Run existing test suites
- Grep for `TODO`, `FIXME`, `HACK` introduced by agents

#### 5b: Re-analyze changed files
Launch audit agents scoped to `git diff --name-only`. Check for:
- **Multi-agent conflicts**: inconsistent edits to shared files
- **Incomplete wiring**: components created but not connected
- **Type drift**: tests/consumers using old shapes after type changes
- **SQL mismatches**: queries assuming nonexistent constraints
- **Security**: injection, unsafe casts, unhandled rejections

#### 5c: Decision
- Minor issues → fix inline
- Significant → new concerns, loop to Phase 3
- Shared-file conflicts → single agent reads ALL changes

**Gate**: User decides: close, fix, or loop.

---

### Phase 6: CLOSE

- Update concern files: STATUS: done, Resolution notes
- Update 00-overview.md with completion stats
- If CALIBRATION.md exists, append learnings
- If this was a new codebase pattern, suggest `/plan calibrate` to bake learnings into the skill

---

## Calibrate

**Scope**: `/plan calibrate`

Same mechanism as `/remediate calibrate`:
1. Read `plans/CALIBRATION.md` RULES section
2. Read this skill file
3. For each rule, update the relevant section of the skill
4. Present diff for approval

---

## Scope Interpretation

| Input | Behavior |
|-------|----------|
| `<goal description>` | Full pipeline: explore → design → decompose |
| `plans/<name>` | Skip explore/design, execute existing plan |
| `execute plans/<name>` | Execute a plan that was created with "just plan" |
| `audit` | Skip to Phase 5 on recent changes |
| `calibrate` | Bake CALIBRATION.md rules into this skill |

## Key Behaviors

- **Explore before designing** — understand what exists before deciding what to build
- **Design before decomposing** — make key decisions before writing concern files
- **TOUCHES analysis** — identify shared files before batching to prevent conflicts
- **Never guess file contents** — always read before editing
- **Preserve existing patterns** — new code should look like it belongs
- **Verify blockers at execution time** — don't trust the plan blindly
- **Propagate context between batches** — agents must know what previous agents did
- **Agents report anomalies** — don't force, report

## Differences from /remediate

| Aspect | /remediate | /plan |
|--------|-----------|-------|
| Trigger | Something is broken | Something needs to be built |
| Phase 1 | Gap analysis (find problems) | Explore (map what exists) |
| Phase 2 | Plan (group problems into fixes) | Design (make architectural decisions) |
| Concern format | Problem → Evidence → Fix | Goal → Approach → Verify |
| Typical complexity | More mechanical fixes | More architectural concerns |
| Design doc | No | Yes (DESIGN.md) |
