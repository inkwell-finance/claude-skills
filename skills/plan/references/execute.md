# /plan — Phase 4 EXECUTE + Phase 5 AUDIT (full bodies)

Moved verbatim from SKILL.md; SKILL.md keeps the phase headings and pointers.

### Phase 4: EXECUTE (optional)

User can say "execute" or "just plan" (skip to CLOSE).

If executing, follow the same rules as `/remediate` Phase 3:

#### Execution engine

**Prefer the Workflow tool** for any plan with 3+ concerns (invoking this skill and saying "execute" is the user's opt-in to multi-agent orchestration). Express EXECUTE as a workflow script: batches as `pipeline()`/`parallel()` stages, implementer outputs schema-validated, the inline reviewer as a mandatory verify stage. Two reasons this beats hand-driven Agent batches:
- **Determinism** — the reviewer stage structurally cannot be skipped, and context propagation between batches is code, not discipline.
- **Resume** — if the session or daemon dies mid-plan, relaunch with `resumeFromRunId` and completed concerns return cached instead of being re-implemented. (A past pipeline run lost its daemon after concern 1 of 4 and the rest had to be finished by hand — resume exists for exactly this.)

Hand-driven Agent batches remain fine for tiny plans (1-2 concerns).

#### Batch formation
1. Zero-blocker tasks first
2. Model by COMPLEXITY tag
3. **SAME-FILE RULE**: overlapping TOUCHES → same agent or sequential
4. **CROSS-REPO ATOMIC RULE**: shared type changes → same agent/batch for all consumers
5. Max 10 agents per batch

#### Isolation (mandatory for parallel batches)
Parallel implementers must never share a working tree — TOUCHES analysis *predicts* conflicts, isolation *enforces* it, and TOUCHES lists are guesses made before the code was read. For any batch with more than one implementer:
- Give each implementer `isolation: 'worktree'` (Agent tool and Workflow `agent()` both support it). Each agent commits in its own worktree; the orchestrator merges the batch branches sequentially in dependency order after review.
- **Fleet mode**: for large plans where daemon supervision pays off, dispatch the batch to the omp-squad fleet via `/squad` instead — units are worktree-isolated and land via proven merges. Offer fleet mode only if `command -v omp-squad` succeeds; if the binary is absent, note it and stay on Workflow + worktrees.

Single-agent batches may edit in place.

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
{additional rules from CALIBRATION.md if it exists}

1. Read the relevant source files first
2. {instructions from Approach section}
3. Write the code. Edit existing files where possible. Create new files only when necessary.

IMPORTANT: If you discover the task is already done, partially done,
or blocked differently than expected, REPORT THIS instead of forcing.
```

#### Inline review (per batch)

After each batch of implementers, run a **fable reviewer** (opus when fable is unavailable) before advancing. Same mechanism as `/remediate`:

| Step | Role | Model | Input | Output |
|------|------|-------|-------|--------|
| 1 | **Reviewer** | fable (opus when unavailable) | All diffs from this batch + their concern files | Pass/fail per agent + issues list with severity |
| 2 | **Fixer** | sonnet (or per-complexity) | Reviewer's issues list | Targeted fixes for failed items |

**Mechanical batches** (< 3 files per concern, no shared types): run the reviewer at low effort rather than skipping it — the workflow expression above promises a structurally unskippable verify stage, and a skip rule here would break that guarantee.

Reviewer prompt template: read the fenced **Reviewer prompt template** block in `~/.claude/skills/remediate/SKILL.md` (Phase 3, "Inline review" section) — read the file directly rather than invoking `/remediate`.

#### After each batch (post-review)
- TodoWrite progress update
- Scorecard (task, model, time, result, review pass/fail)
- Shared-file changelog for next batch
- Unblocked task check

**Gate**: User approves each batch (or "keep going" for autonomous).

---

### Phase 5: AUDIT

If Phase 4 was executed, audit is **mandatory**. Same as `/remediate`:

#### 5a: Self-check
- Type check / lint / build across affected repos
- Run existing test suites
- Run `/verify` on the primary user-visible flow the plan shipped — drive the behavior end-to-end, don't stop at green tests
- Grep for `TODO`, `FIXME`, `HACK` introduced by agents

#### 5b: Cross-batch consistency review
Run `/code-review` at high effort on the full diff first — it owns line-level correctness findings. Then, with inline review catching per-batch issues and `/code-review` catching diff-visible bugs, launch a **fable audit agent** (opus when fable is unavailable) with the full `git diff` across ALL batches, focused on what a diff review can't see:
- **Multi-agent conflicts**: inconsistent edits to shared files across different batches
- **Incomplete wiring**: components created in one batch but not connected by a later batch
- **Type drift**: tests/consumers using old shapes after cross-batch type changes
- **SQL mismatches**: queries assuming nonexistent constraints
- **Security**: injection, unsafe casts, unhandled rejections
- **Goal completion**: does the sum of all changes actually achieve the original goal from Phase 2?

#### 5c: Decision
- Minor issues → fix inline
- Significant → new concerns, loop to Phase 3
- Shared-file conflicts → single agent reads ALL changes

**Gate**: User decides: close, fix, or loop.
