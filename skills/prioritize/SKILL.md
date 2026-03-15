---
name: prioritize
description: Audit all plans against actual codebase implementation, identify gaps, stubs, and unimplemented work, then produce a ranked implementation priority order. Use when the user wants to know what to build next.
argument-hint: "[scope]"
disable-model-invocation: true
---

# Prioritize

Audit all plans against actual code to produce a ranked implementation order. Answers: "What should we build next, and why?"

```
INVENTORY → VERIFY → DISCOVER → SCORE → RANK → PRESENT
```

---

### Phase 1: INVENTORY

Catalog everything that exists in the plans directory.

1. Read `plans/README.md`, `plans/DEPENDENCIES.md`, `plans/CALIBRATION.md`
2. For each numbered plan directory, read `00-overview.md` (or `DESIGN.md` if no overview)
3. Categorize each plan:
   - **done** — all concerns STATUS: done
   - **partial** — some concerns done, some open/blocked
   - **open** — not started or mostly open
   - **deferred** — explicitly deferred (feature scope, research, blocked)

4. For partial/deferred plans, extract the specific open concerns with their COMPLEXITY, TOUCHES, and BLOCKED_BY

Output: a **plan inventory table** — plan #, name, status, open concern count, deferred items, stated dependencies.

---

### Phase 2: VERIFY

Do NOT trust plan STATUS. Verify against actual code.

Launch parallel Explore agents (one per plan group) to check:

1. **"Done" plans with suspicious gaps**: For plans marked done, spot-check that key files/functions mentioned in TOUCHES actually exist and contain the expected implementation (not stubs)
2. **"Open" plans**: Confirm they're genuinely unimplemented
3. **"Partial" plans**: Identify exactly which concerns are done vs open in source

For each concern, check:
- Do the files in TOUCHES exist?
- Do they contain the types/functions/classes described in the plan?
- Are they stubs (placeholder returns, TODO comments, empty implementations) or real?
- Are they wired to consumers (imported and called)?

Output: a **verified status table** — correcting any stale STATUS fields. Flag discrepancies (plan says done but code is missing, or plan says open but code exists).

---

### Phase 3: DISCOVER

Find implementation gaps NOT covered by any existing plan.

Launch parallel Explore agents to search for:

1. **Stubs and placeholders**: TODO, FIXME, HACK, STUB, "not implemented", placeholder returns, hardcoded values, `as any` casts on critical paths
2. **Dead code and unused exports**: Functions/classes defined but never imported
3. **Feature flags and disabled functionality**: Commented-out code blocks, environment variable gates
4. **Missing test coverage**: Critical paths with no test files
5. **Incomplete wiring**: Components instantiated but not connected to consumers
6. **Fake implementations**: Files with "stub", "mock", "fake" in names that are used in production paths

Cross-reference each finding against existing plans:
- If covered by an existing plan → note it
- If NOT covered → flag as **unplanned gap**

Output: a **gap report** — unplanned gaps with file paths, severity, and suggested plan assignment.

---

### Phase 4: SCORE

Score each open item (verified open concerns + unplanned gaps) on 5 dimensions:

| Dimension | Weight | How to assess |
|-----------|--------|---------------|
| **Dependency value** | 30% | How many other items does this unblock? Check DEPENDENCIES.md + cross-plan BLOCKED_BY references. Items that unblock 3+ others score highest. |
| **Foundation value** | 25% | Does this provide infrastructure (types, data, APIs) that multiple future features build on? Data layers and protocol types score highest. |
| **Risk reduction** | 20% | Does this fix a security gap, data integrity issue, or correctness bug? Security > correctness > robustness. |
| **Effort efficiency** | 15% | LOC estimate vs value delivered. Quick wins (high value, low effort) score highest. |
| **Independence** | 10% | Can this be built without waiting for other items? Items with zero blockers score highest. |

Score each item 1-5 per dimension, compute weighted total.

---

### Phase 5: RANK

Produce the final priority order by:

1. Sort by weighted score (descending)
2. Apply dependency constraints — if A blocks B and both score similarly, A goes first
3. Group into implementation tiers:
   - **Tier 1 — Now**: Score >= 4.0, zero or minimal blockers
   - **Tier 2 — Next**: Score >= 3.0, blockers resolved by Tier 1
   - **Tier 3 — Later**: Score >= 2.0, requires Tier 1+2 foundation
   - **Tier 4 — Backlog**: Score < 2.0, nice-to-have, or blocked by external factors
4. Within each tier, identify parallelization opportunities (items with no cross-dependencies)

---

### Phase 6: PRESENT

Present to the user:

#### Summary
- Total open items: X (Y from existing plans, Z unplanned gaps)
- Plans with stale STATUS: list
- Unplanned gaps found: count + brief descriptions

#### Priority Table
| Tier | # | Item | Plan | Score | Blockers | LOC est | Rationale |
|------|---|------|------|-------|----------|---------|-----------|

#### Dependency Graph
ASCII diagram showing which items unblock which.

#### Recommended Execution Sequence
Concrete batch order with parallelization notes, following the same batch formation rules as `/plan` and `/remediate`.

#### Unplanned Gaps
Items not covered by any plan, with recommendation: create new plan, add to existing plan, or deprioritize.

**Gate**: User decides which tier(s) to execute and whether to create plans for unplanned gaps.

---

## Scope Interpretation

| Input | Behavior |
|-------|----------|
| (no args) | Full audit: all plans + full codebase scan |
| `plans` | Plans-only: inventory + verify, skip DISCOVER |
| `gaps` | Gaps-only: skip plans, run DISCOVER + SCORE on findings |
| `plans/<name>` | Single plan: deep verify + score its open concerns |
| `quick` | Fast mode: inventory + verify only, skip DISCOVER and detailed scoring. Use for a quick status check. |

## Key Behaviors

- **Never trust STATUS** — always verify against source code
- **Cross-reference everything** — gaps found in code should map to plans, plans should map to code
- **Score objectively** — use the 5-dimension rubric, not gut feel
- **Present actionably** — the output should directly inform what to `/plan` or `/remediate` next
- **Preserve context** — reference specific file paths and line numbers so findings are verifiable
- **Update plans** — if verification reveals stale STATUS fields, offer to fix them
