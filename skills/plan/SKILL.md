---
name: plan
description: Decompose a feature, migration, or initiative into a persistent plans/<name>/ directory of concern docs (STATUS/PRIORITY/COMPLEXITY/TOUCHES/BLOCKED_BY frontmatter) with dependency graphs and optional batched parallel execution. Use when the user wants to BUILD something non-trivial — "plan this", "break this down", "scope this migration", "make a plan for X" — not to fix what's broken (/remediate), not for small direct edits (just make them), and not for pure fleet dispatch of already-planned units (/squad). Also handles executing or auditing an existing plans/<name> directory ("execute plans/<name>", "/plan audit") and "/plan calibrate". Feeds the /plan-to-plane → /promote-issue → /claim-and-implement pipeline.
argument-hint: "<goal>"
---

# Plan

Decompose a goal into structured, executable plans. Then optionally execute them.

Unlike `/remediate` (reactive — find what's broken, fix it), `/plan` is proactive — the user has a goal, this skill decomposes it into work.

```
WIP-CHECK → EXPLORE → DESIGN → DECOMPOSE → (optional) EXECUTE → AUDIT → CLOSE
```

**Gate policy (headless).** Interactive runs stop at every gate below. Headless runs (background job, cron, or a research→plan→implement pipeline) generalize the Phase 0 rule to all gates: the EXPLORE, DESIGN, and DECOMPOSE gates degrade to recorded checkpoints — write the landscape, design brief, and decomposition to the plan dir and note "auto-approved: headless" plus any assumptions made in `00-overview.md` under `## Notes`. EXECUTE never auto-starts headless unless the invoking pipeline explicitly authorized execution; the default headless terminal state is a decomposed plan, stopped after DECOMPOSE with the open choices reported. Headless auto-approval governs `/plan`'s own phase checkpoints and never overrides a concern's `MODE: hitl` — an agent answering the human's side of a decision is a correctness violation, not initiative.

---

### Phase 0: WIP-CHECK (pre-flight)

**Why this phase exists.** `/plan` is cheap to invoke; plan doc completion is invisible. Without a forcing function, plans accumulate: 30+ on-disk directories, 200+ concerns marked `STATUS: open` long after the underlying work shipped. The pile looks infinite because the sink is plugged — STATUS never gets updated, so the counter only ever goes up. This phase makes the pile visible before a new one is added to it.

**What to do:**

1. Run the WIP scanner against the repo root:

   ```bash
   python3 ~/.claude/skills/wip/lib/scan.py <repo-root> --format summary --rank
   ```

2. If the output shows **0 plans with open concerns**, proceed silently to Phase 1. Clean slate — no forcing function needed.

3. Otherwise, show the user the ranked table (or at minimum the top 10) and ask an explicit question:

   > You have **N plans with open concerns** (oldest: `<plan>` at `<date>`). Options:
   >
   > - **resume one** — I'll hand off the next unblocked concern in that plan via `/wip resume <plan>`
   > - **triage one** — walk its open concerns interactively and close the ones that are already done (`/wip triage <plan>`)
   > - **sync first** — run `/sync-plans` to pull current Plane state for promoted concerns (closes the easy cases automatically)
   > - **proceed anyway** — start this new plan on top of the existing pile (say "proceed")
   >
   > How do you want to move?

4. **In interactive sessions, do not proceed to Phase 1 without an answer.** Auto-mode is not a license to skip this — the forcing function only works if it fires. The exception: if the user's original `/plan <goal>` invocation was explicitly framed as "continue X" or "supersede X", treat that as equivalent to a pre-answered prompt and skip the question. The same applies when the invocation targets an existing plan (`plans/<name>`, `execute plans/<name>`, or `audit`): resuming existing work is the gate's desired outcome, so skip Phase 0 entirely.

5. Escape hatches:
   - User says "just plan anyway" or equivalent → proceed to Phase 1, note the choice in the final report.
   - User says "resume X" → hand off to `/wip resume X` and terminate this `/plan` invocation.
   - User says "triage X" → hand off to `/wip triage X` and terminate.
   - User says "sync first" → run `/sync-plans`, then re-run Phase 0.

6. **Headless runs** (background job, cron, or a pipeline like research→plan→implement): the gate cannot block on a human, and deadlocking the pipeline is worse than skipping the question. Instead: still run the scanner, record the snapshot in the new plan's `00-overview.md` under `## Notes` ("proceeded over N open plans; oldest: `<plan>` at `<date>`"), and continue to Phase 1. The forcing function fires at the next interactive `/plan` or `/wip` — the debt is logged, not hidden.

**Gate:** user has picked one of (resume / triage / sync / proceed / cancel). Silent progression is not allowed.

**Why the gate is load-bearing:** without it, the scanner is noise. The friction is the feature — one explicit "are you sure you want to start another one?" at the right moment is worth more than any post-hoc tooling.

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

**For simple goals** — one concern, no architectural choice, no cross-repo effect, no new external dependency — skip this phase: omit `DESIGN.md` and record the chosen approach in `00-overview.md` under `## Notes`. Anything else runs DESIGN.

**For non-trivial goals**, use the adversarial design team:

| Round | Role | Model | Count | Input | Output |
|-------|------|-------|-------|-------|--------|
| 1 | **Designer** | sonnet | 1 | Landscape summary + goal | Draft design: 2-3 approaches with tradeoffs, key decisions, risks, recommendation |
| 2 | **Red Team** | fable (opus when unavailable) | 2 (parallel) | Draft design + landscape | Critique: failure modes, scaling issues, edge cases, missed alternatives, wrong assumptions |
| 3 | **Arbiter** | fable (opus when unavailable) | 1 | Design + both critiques | Final design: resolves concerns, strengthens weak points, makes the call |

**Why adversarial design**: A single agent designing in isolation produces plausible designs that miss failure modes. A past run shipped a confident "fix" that turned out to be a no-op precisely because one agent analyzed the problem alone and nothing attacked its reasoning. Two red teamers arguing with the design catches the "this works until..." class of issues before any code is written.

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

**Writing standard for `DESIGN.md`:**
- Write for a staff engineer reviewing direction, not for an implementer reading source.
- Keep it short: target 1-2 pages.
- Use Markdown headings, bullets, and small tables only.
- Do not include code, file-level diffs, API payloads, or low-level implementation steps.
- Name the user-visible outcome, system boundary, tradeoffs, risks, and the chosen path.
- If source-level detail matters, put it in concern files under `## Approach`, not in `DESIGN.md`.

Write to `plans/<goal-name>/DESIGN.md`:
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

**DESIGN exit path**: if Open Questions can't resolve this session, do not force-decompose — write `plans/<name>/` now with each open question as a decision concern (`MODE: hitl` for preference/judgment calls, `COMPLEXITY: research` for investigable ones), `BLOCKED_BY` chains where decisions depend on each other, remaining fog filed in `00-overview.md`'s `## Not yet specified`, and the line `DECOMPOSE: pending` under `## Notes`. Offer `/plan-to-plane` filing for the decision concerns. Resolve one at a time, recording its gist row, STATUS, and fog graduation before starting the next — there is no per-session ticket limit, only the invariant that every resolution gets recorded before moving on. Headless: this replaces force-decomposition as the terminal state.

---

### Phase 3: DECOMPOSE

Break the design into executable concern files. Same structure as `/remediate` plans.

**Fog test**: write a concern only when the underlying question is *phrasable precisely now*, even if it isn't yet answerable. A question that's still too vague to phrase precisely stays a single loose bullet in `## Not yet specified` — never pre-sliced into concern-sized pieces before it's ripe.

#### Plan directory
```
plans/<goal-name>/
├── DESIGN.md              # From Phase 2
├── 00-overview.md          # Scope, deps, remediation order
├── 01-concern.md           # First task
├── 02-concern.md           # Second task
└── ...
```

#### Human-readable plan docs

`DESIGN.md` and `00-overview.md` are product and architecture orientation docs. They must be concise, readable Markdown.

Rules:
- Staff-level, human-understandable summary.
- No code blocks.
- No source walkthroughs.
- No generated-sounding filler.
- Prefer bullets and short tables over paragraphs.
- Explain what changes, why it matters, what order to do it in, and what can run in parallel.
- Leave file paths and implementation detail to the concern files.

`00-overview.md` should fit on one screen where possible:
```markdown
# <Goal>

## Outcome
- What the user or operator gets when this ships.

## Work
| Concern | Why it exists | Complexity | Touches |

## Order
| Batch | Concerns | Why together |

## Dependency graph
| Concern | Blocked by | 30s check |

## Not yet specified
- (none)

## Out of scope
- <what was ruled out> — why — link to the cancelled concern

## Decisions so far
- [<concern title>](NN-file.md) — <one-line gist>

## Notes
- Only decisions a human needs before starting.
```

#### Concern file format
```markdown
# Title
STATUS: open
PRIORITY: p0 | p1 | p2
REPOS: affected repos
COMPLEXITY: mechanical | architectural | research
TOUCHES: list of file paths this will create or modify
BLOCKED_BY: NN, NN   (optional — sibling concern numbers. Duplicate every dependency edge here, not only in 00-overview.md: /plan-to-plane's Todo-vs-Backlog state mapping and /wip resume's unblocked filter read BLOCKED_BY from this frontmatter; only Plane relation creation falls back to the overview table)
MODE: hitl | afk   (optional, default afk — hitl means only a human may resolve this; autonomous consumers must not claim it. MODE is the ownership axis, COMPLEXITY the effort axis; they compose. Unrecognized values are treated as hitl.)
PLANE: <PROJECT>-<NN>   (optional — added by /plan-to-plane when the concern is filed; /plan-to-plane keys off it for idempotency, /sync-plans for state reconciliation, and /claim-and-implement preserves it for traceability, so never strip it)

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

Judgment roles (red team, arbiter, reviewer) run on fable, falling back to opus when fable is unavailable.
Implementation runs on sonnet.
Scouts and verifiers run on sonnet at low effort — never haiku.

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

**Gate**: Present the decomposition to user. Confirm concern list, batch order, and complexity and mode assignments. Offer to file the plan to Plane via `/plan-to-plane` — filing at decompose time (rather than remembering at CLOSE) is what makes `/sync-plans` and `/promote-issue` able to track the work.

---

### Phase 4: EXECUTE (optional)

Full phase body: `references/execute.md` (execution engine, batch formation, prompt templates, inline review).
- **Isolation**: parallel implementers never share a working tree — every multi-agent batch gets `isolation: 'worktree'` (or is dispatched to the /squad fleet).
- **Crash recovery**: prefer the Workflow tool (3+ concerns) so a dead session resumes via `resumeFromRunId` with completed concerns returned cached.

---

### Phase 5: AUDIT

If Phase 4 was executed, audit is **mandatory** — full body (self-check, cross-batch consistency review, decision) in `references/execute.md`.

---

### Phase 6: CLOSE

**This phase is the sink. Without it the WIP counter drifts upward forever** (see the 214-open-0-closed pattern that motivated Phase 0). Never end a /plan run without actually running this phase, even if the user says "we're done" — running it is cheap; not running it adds to the pile.

**Plan-only runs** (Phase 4 skipped): CLOSE finalizes the planning artifact, not the work. Leave every new concern `STATUS: open`, write no `## Resolution`, report the plan path and the scanner's new WIP count (it is *expected* to grow by this plan's concerns), and stop. The closure procedure below applies only to concerns actually implemented and verified in this run.

- **Update every implemented concern's STATUS** — `done` for the ones that shipped (write `done`, not `closed`: `/plan-to-plane` and `/claim-and-implement` parse `done`; the WIP scanner treats the two as synonyms but the siblings don't), `cancelled` for ones abandoned mid-plan, `blocked` for ones waiting on an external dependency. Append a brief `## Resolution` section citing the commit SHA or the evidence of shipping. Every `cancelled` concern also gets an `## Out of scope` ledger line (gist — why — link) so a deliberate scope-out never reads as abandonment.
- **Update 00-overview.md** with completion stats (N/M closed, remaining blockers, cross-plan dependencies discovered). Empty the fog: every `## Not yet specified` bullet must graduate into a concern or move to `## Out of scope` with a rationale — CLOSE never leaves fog non-empty. Append your own `## Decisions so far` row for each concern this run closed (keyed by the concern link, idempotent) — never edit another closer's row; a contradiction gets a superseding row.
- **If a concern has a `PLANE:` pointer and was implemented in this run**, close its Plane issue via the plane MCP as well (move it to Done — the same close step `/claim-and-implement` performs). Plane is source of truth for open-status: leave the issue in Todo and the next `/sync-plans` run will rewrite your `done` back to `open`. For Plane-filed concerns this run did NOT implement, don't mutate Plane from here; recommend `/sync-plans` if Plane state might be ahead of the plan docs.
- **If CALIBRATION.md exists**, append learnings.
- **If this was a new codebase pattern**, suggest `/plan calibrate` to bake learnings into the skill.
- **Final check**: re-run the Phase 0 scanner. The plan you just closed should either drop off the "plans with open concerns" list entirely or show a significantly reduced `open_count`. If it doesn't, you skipped a concern — loop back.

The discipline of closing STATUS is load-bearing. A plan with real work done but no STATUS updates looks identical on-disk to an abandoned plan. The scanner can't tell them apart, which is why the 34-plan pile looked unbounded to begin with.

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
| `plans/<name>` where `00-overview.md` has `DECOMPOSE: pending` | Resume Phase 2 DESIGN from the decisions index; never execute |

## Key Behaviors

- **Isolate parallel implementers** — worktrees (or /squad) for any multi-agent batch; a shared working tree is how parallel agents clobber each other
- **Verify blockers at execution time** — don't trust the plan blindly
- **Agents report anomalies** — don't force, report
- **Strongest model for judgment, not volume** — fable (opus when unavailable) reviews, red teams, arbitrates, and synthesizes; sonnet does the implementation

## Differences from /remediate

| Aspect | /remediate | /plan |
|--------|-----------|-------|
| Trigger | Something is broken | Something needs to be built |
| Phase 1 | Gap analysis (find problems) | Explore (map what exists) |
| Phase 2 | Plan (group problems into fixes) | Design (adversarial: draft → red team → arbiter) |
| Concern format | Problem → Evidence → Fix | Goal → Approach → Verify |
| Typical complexity | More mechanical fixes | More architectural concerns |
| Design doc | No | Yes (DESIGN.md with red team concerns) |
| Shared | Inline fable/opus reviewer per batch, context propagation, calibration loop |
