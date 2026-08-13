# plans/ Scaffold — Supporting File Content Specs

Full content requirements for the three supporting files created in Phase 2 (PLAN).

## `plans/CONVENTIONS.md`

Must contain all of the following sections:

1. **File Format** — the full concern file template (STATUS, PRIORITY, REPOS, COMPLEXITY, TOUCHES, Problem, Evidence, Fix, Cross-Repo Side Effects, Verify, Resolution)
2. **COMPLEXITY Field** — table mapping mechanical/architectural/research to meaning and model assignment
3. **Plan Lifecycle** — state machine: `open → in-progress → done | blocked`. Instructions for starting work (set status, check DEPENDENCIES.md), completing work (set status, add Resolution section, do NOT delete the file), and handling blocks (set status, add BLOCKED_BY)
4. **Resolution Format** — when STATUS becomes done, append: Completed date, PR/Commit link, Notes (anything surprising or learned)
5. **Plan Structure** — each plan directory has `00-overview.md` (scope table, local deps, external deps, remediation order) plus numbered concern files
6. **Cross-Plan Dependencies** — how `00-overview.md` owns local deps while `DEPENDENCIES.md` maps cross-plan edges
7. **Learning From Completed Plans** — Resolution notes capture underestimates, overestimates, missed dependencies, wrong assumptions, and techniques that worked. Future analyses read these notes to calibrate severity, identify surprise-prone repos, and improve verification steps.

## `plans/README.md`

Must contain:

1. **Context line** — date, what was analyzed, relationship to prior runs if any
2. **Plans table** — columns: #, Plan (linked), Concerns count, p0/p1/p2 counts, Status, Completed date
3. **Batch Execution Order** — reference to DEPENDENCIES.md plus summary table (batch #, what plans/concerns, est. agents, model mix)
4. **Execution Stats** (added during/after execution) — total concerns, agents by model, open items remaining
5. **Calibration reference** — pointer to CALIBRATION.md if it exists
6. **Adding a New Plan** — instructions: create dir, write 00-overview.md, write concern files, add to table, add edges to DEPENDENCIES.md

## `plans/DEPENDENCIES.md`

Must contain:

1. **Repo Dependency Graph** — ASCII diagram showing which repos import from which (protocol → trader/coordinator/researcher, contracts → researcher/coordinator, etc.)
2. **Change Impact Matrix** — table with columns: Plan/Concern, Primary Repo, Must Also Change, Regression Risk. One row per concern that has cross-repo side effects. Include specific risk description (e.g., "if coordinator enforces sigs before researcher signs → all proposals rejected")
3. **Atomic Groups** — list of concern sets that MUST ship together or in strict sequence. Explain why (shared file, protocol type change, etc.)
4. **Sequential Constraints** — ordered pairs where A must complete before B, with rationale
5. **Parallel-Safe** — list of concerns/plans that are safe to run independently
6. **Batch Plan** — table: batch #, plans/concerns included, agent count, model assignment, rationale for grouping
