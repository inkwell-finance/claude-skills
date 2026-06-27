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
                ↑___________________________________|
        AUDIT escalates to DESIGN on a design-level failure, or loops to DECOMPOSE on an implementation failure
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

**For simple goals**, skip this phase — go straight to DECOMPOSE.

**For non-trivial goals**, use the adversarial design team:

| Round | Role | Model | Count | Input | Output |
|-------|------|-------|-------|-------|--------|
| 1 | **Designer** | sonnet | 1 | Landscape summary + goal | Draft design: 2-3 approaches with tradeoffs, key decisions, risks, recommendation |
| 2 | **Red Team** | opus | 2 (parallel) | Draft design + landscape | Critique: failure modes, scaling issues, edge cases, missed alternatives, wrong assumptions |
| 3 | **Arbiter** | opus | 1 | Design + both critiques | Final design: resolves concerns, strengthens weak points, makes the call |

**Why adversarial design**: A single agent designing in isolation produces plausible designs that miss failure modes. The epsilon false-fix in Run 4 was exactly this — a single-agent analysis error. Two opus red teamers arguing with the design catches the "this works until..." class of issues before any code is written.

**Red Team prompt template:**
```
You are adversarially reviewing a design for: {goal}

LANDSCAPE: {landscape summary from Phase 1}
DRAFT DESIGN: {designer output}

Your job is to ATTACK this design. Find:
1. Failure modes the designer didn't consider (concurrency, partial failure, data loss)
2. Scaling bottlenecks that only appear at load
3. Edge cases that break the happy path
4. Simpler alternatives the designer missed
5. Assumptions that are wrong or unverified
6. Dependencies that don't exist or work differently than assumed

For each issue:
- SEVERITY: critical (blocks shipping) | significant (causes bugs) | minor (suboptimal)
- EVIDENCE: why you believe this is a real issue, not theoretical
- SUGGESTION: how to address it (or "needs more research")

Be specific. "This might not scale" is useless. "With 1000 concurrent writers, the single Redis LPOP becomes a bottleneck because..." is useful.
```

**Arbiter behavior:**
- Critical issues from red team MUST be addressed in the final design
- Significant issues should be addressed or explicitly accepted as known risks with mitigation
- If red teamers disagree with each other, the arbiter weighs the evidence, doesn't average
- If a red team concern reveals the design is fundamentally wrong, the arbiter can reject the draft and restart Round 1 with new constraints (max 1 restart)

Output: a **design brief** — approach chosen, key decisions made, risks identified, red team concerns addressed.

Write to `plans/####-<goal-name>/DESIGN.md`:
The #### should be a logical increment from the last plan in the repo.
```markdown
# Design: <goal>

## Approach
## Key Decisions
| Decision | Choice | Alternatives considered | Rationale |
## Risks
## Red Team Concerns Addressed
| Concern | Severity | Resolution |
## Open Questions (if any — resolve before DECOMPOSE)
```

**Gate**: User approves design before decomposition. Open questions must be resolved.

---

### Phase 3: DECOMPOSE

Break the design into executable concern files. Same structure as `/remediate` plans.

#### Plan directory
```
plans/####-<goal-name>/
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

#### Model assignment

**By implementation complexity (for implementer agents):**
| Tag | Model | Use when |
|-----|-------|----------|
| `mechanical` | haiku | Clear implementation, schema, config, boilerplate, < 10 files |
| `architectural` | sonnet | System integration, cross-repo, new abstractions, 10+ files |
| `research` | opus | Critical design decisions requiring deep reasoning about tradeoffs |

**By team role (for non-implementer agents):**
| Role | Model | Rationale |
|------|-------|-----------|
| Designer | sonnet | Produces draft designs — good enough for red team to attack |
| Red Team | opus | Finding non-obvious failure modes requires strongest reasoning |
| Arbiter | opus | Resolving conflicting critiques, making the final call |
| Reviewer | opus | Judgment on correctness, completeness, downstream implications |
| Scout/Verifier | haiku | Data gathering, existence checks |

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

#### Cost & scale estimate
Before presenting, tally the planned fan-out: count agents by model across all batches (implementers by COMPLEXITY tag + the per-batch opus reviewer + the audit agent). Present this at the gate as `N haiku + M sonnet + K opus agents across B batches`, so the user can cut **scope** — not quality — if it's too large. The human already approves the decomposition; surfacing the cost here makes that approval informed instead of discovering the bill after the fact.

**Concern-count ceiling**: if a single plan carries more than ~12 `architectural`/`research` concerns, treat that as a signal the goal is too big for one plan — propose splitting it. A bloated plan is a scoping problem, never a model-assignment problem. Do **not** "solve" it by downgrading concerns below their COMPLEXITY tag; that trades correctness for cost and breaks the reason each tag exists (see Phase 4 budget circuit-breaker).

**Gate**: Present the decomposition to user. Confirm concern list, batch order, complexity assignments, and the cost/scale estimate.

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

#### Inline review (per batch)

After each batch of implementers, run an **opus reviewer** before advancing. Same mechanism as `/remediate`:

| Step | Role | Model | Input | Output |
|------|------|-------|-------|--------|
| 1 | **Reviewer** | opus | All diffs from this batch + their concern files | Pass/fail per agent + issues list with severity |
| 2 | **Fixer** | sonnet (or per-complexity) | Reviewer's issues list | Targeted fixes for failed items |

**When to skip:** Batch contains only haiku mechanical fixes (< 3 files each, no shared types).

See `/remediate` Phase 3 for the full reviewer prompt template.

#### Checkpoint per batch (git-native)
Use git as the rollback boundary — never hand-snapshot a subset of touched files (that loses atomicity and leaves the tree half-reverted).
- **Before batch N**: confirm a clean baseline. The working tree should be committed (or stashed) so the batch starts from a known-good state. Record that commit as `checkpoint-batch-{N-1}` (a tag or noted SHA).
- **After batch N passes inline review**: commit the batch as one atomic unit and tag it `checkpoint-batch-{N}`. This is the green state the next batch builds on.
- **On audit failure for batch N** (see Phase 5): `git reset --hard checkpoint-batch-{N-1}` back to the last green state, then re-decompose (or re-design) rather than patching a corrupted tree forward.

This mirrors the worktree-isolation + proven-merge model the squad fleet uses: every unit lands from a known-good base or not at all. The inline reviewer (above) already catches most single-batch defects before they land — the checkpoint's real value is **cross-batch** failures that only surface in AUDIT, where you need a clean point to roll back to.

#### Autonomous budget circuit-breaker
When the user says "keep going" (no per-batch gate), keep a running tally of agents spawned by model. If it crosses the Phase 3 estimate by a meaningful margin, **pause and ask** — report cost so far, concerns remaining, and offer continue / cut scope / stop. **Never** silently downgrade a concern below its COMPLEXITY tag, and never skip the opus reviewer or audit agent to stay under budget: a missed cross-batch bug costs a full loop cycle — far more than the model call it saved. The whole "opus for judgment" design exists because cheap bugs caught late are expensive. Budget forces scope reduction *with a human in the loop*, not quality reduction behind their back.

#### After each batch (post-review)
- TodoWrite progress update
- Scorecard (task, model, time, result, review pass/fail)
- Commit/tag the batch as `checkpoint-batch-{N}` (the rollback boundary for the next batch)
- Shared-file changelog for next batch
- Unblocked task check

**Gate**: User approves each batch (or "keep going" for autonomous — subject to the budget circuit-breaker above).

---

### Phase 5: AUDIT

If Phase 4 was executed, audit is **mandatory**. Same as `/remediate`:

#### 5a: Self-check
- Type check / lint / build across affected repos
- Run existing test suites
- Grep for `TODO`, `FIXME`, `HACK` introduced by agents

#### 5b: Cross-batch consistency review
With inline review catching per-batch issues, this phase focuses on **cross-batch consistency**. Launch an **opus audit agent** with the full `git diff` across ALL batches. Check for:
- **Multi-agent conflicts**: inconsistent edits to shared files across different batches
- **Incomplete wiring**: components created in one batch but not connected by a later batch
- **Type drift**: tests/consumers using old shapes after cross-batch type changes
- **SQL mismatches**: queries assuming nonexistent constraints
- **Security**: injection, unsafe casts, unhandled rejections
- **Goal completion**: does the sum of all changes actually achieve the original goal from Phase 2?

#### 5c: Decision
- Minor issues → fix inline
- Significant *implementation* issues → new concerns, loop to Phase 3 (DECOMPOSE)
- **Design-level failure** → loop to Phase 2 (DESIGN), not Phase 3. This is when the audit shows the chosen *approach* is wrong — not a botched concern, but a flaw in DESIGN.md that re-decomposing the same design would only reproduce (e.g., 5b's "goal completion" check fails because the architecture can't actually achieve the goal). Re-run the adversarial design team with the audit findings as new input; the arbiter's restart cap applies (max 1 design loop) before escalating to the user. Looping to DECOMPOSE here just executes the same broken plan twice.
- Shared-file conflicts → single agent reads ALL changes
- Corrupted/inconsistent tree → `git reset --hard` to the last green `checkpoint-batch-{N}` (Phase 4), then re-decompose or re-design rather than patching forward

**Gate**: User decides: close, fix, loop to DECOMPOSE, or escalate to DESIGN.

---

### Phase 6: CLOSE

- Update concern files: STATUS: done, Resolution notes
- Update 00-overview.md with completion stats
- If CALIBRATION.md exists, append learnings — **from clean runs, not just failures.** On a run that completed with zero review/audit failures, record the *falsifiable* signals worth repeating: which COMPLEXITY→model assignments held (e.g., "haiku cleared all 6 mechanical concerns with zero review failures → the mechanical threshold is well-calibrated here"), which decomposition shapes avoided shared-file conflicts, which batch orderings parallelized cleanly. Scope positive learnings to concrete, checkable claims — never vibes like "the design was clean." Calibration that only learns from mistakes never reinforces what works, so it keeps re-deriving the same good choices.
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
- **Adversarial design for non-trivial goals** — Designer drafts, Red Team attacks, Arbiter resolves
- **TOUCHES analysis** — identify shared files before batching to prevent conflicts
- **Never guess file contents** — always read before editing
- **Preserve existing patterns** — new code should look like it belongs
- **Verify blockers at execution time** — don't trust the plan blindly
- **Propagate context between batches** — agents must know what previous agents did
- **Inline review before next batch** — opus reviewer catches issues while context is fresh
- **Checkpoint per batch** — commit each green batch so audit failures roll back cleanly (`git reset --hard`) instead of patching a corrupted tree forward
- **Audit can escalate to DESIGN** — a design-level failure loops to Phase 2, not Phase 3; never re-execute a broken design
- **Budget forces scope, not quality** — surface the cost estimate at the DECOMPOSE gate; in autonomous mode, pause and ask rather than downgrading models below their COMPLEXITY tag
- **Calibrate from successes too** — clean runs teach which assignments and decompositions to repeat, not just which to avoid
- **Use opus for judgment, not volume** — opus reviews, red teams, arbitrates, and synthesizes; it doesn't do bulk implementation
- **Agents report anomalies** — don't force, report

## Differences from /remediate

| Aspect | /remediate | /plan |
|--------|-----------|-------|
| Trigger | Something is broken | Something needs to be built |
| Phase 1 | Gap analysis (find problems) | Explore (map what exists) |
| Phase 2 | Plan (group problems into fixes) | Design (adversarial: draft → red team → arbiter) |
| Concern format | Problem → Evidence → Fix | Goal → Approach → Verify |
| Typical complexity | More mechanical fixes | More architectural concerns |
| Design doc | No | Yes (DESIGN.md with red team concerns) |
| Shared | Inline opus reviewer per batch, context propagation, calibration loop |
