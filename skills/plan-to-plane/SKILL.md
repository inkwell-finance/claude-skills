---
name: plan-to-plane
description: Translate a /plan output directory (plans/<name>/ with NN-concern.md files) into labeled, moduled, optionally cycled Plane issues via the plane MCP. Use after /plan has decomposed a goal and you want it tracked as open work. Also works on any ad-hoc set of plan docs that follow the STATUS/PRIORITY/COMPLEXITY/TOUCHES frontmatter convention.
argument-hint: "<plan-path> [--module <name>] [--cycle <name>] [--dry-run]"
---

# plan-to-plane

Mechanical bridge from plan-docs-on-disk to Plane-issues-in-browser. The /plan skill produces `plans/<goal-name>/` directories; this skill reads them and creates one Plane work item per concern, preserving priority, complexity, dependencies, and component surface as labels and parent/child links.

```
VERIFY → DISCOVER → MAP → CREATE → BACKFILL
```

---

## Pre-flight checks

1. **Plane resolution + MCP.** Per `reference_plane_mcp.md` (auto-memory, the owner of this contract): resolve the project via `.plane.json` at the repo root → `PLANE_PROJECT_MAP`/`PLANE_PROJECT_ID` env → `list_projects` → ask (then offer to write `.plane.json`); the resolved `identifier` (e.g. `OMPSQ`) prefixes every `PLANE: <IDENT>-NN` pointer this skill writes, and the workspace slug comes from the same config. MCP only — never REST curl fallback.

2. **Plan directory exists.** `<plan-path>` must contain at least one `NN-concern.md` file and ideally a `00-overview.md`. If not, stop.

   **Validate the dependency graph (warning-first, not a hard gate).** Run:
   ```bash
   omp-squad plan-validate <plan-path> --json
   ```
   It reads the plan dir offline and reports dependency **cycles** and **dangling deps** (a concern's `BLOCKED_BY` pointing at a concern that doesn't exist), using the same validator the webapp diagram uses — do NOT re-derive this by hand. Exit 0 = clean; exit 1 = issues found (the `issues[]` in the JSON explain them). If it reports issues, show them to the user and **ask for explicit confirmation before proceeding** — the blocked_by relations you're about to create in Plane will inherit the same cycle/dangling problem. If the `omp-squad` binary isn't on PATH, note that and continue (don't block on the tool being absent).

3. **Cache project metadata** in a single batch of parallel MCP calls:
   - `list_labels(project_id)` — name → id lookup
   - `list_states(project_id)` — Backlog / Todo / In Progress / Done / Cancelled → id lookup
   - `list_modules(project_id)` — module name → id (features may be disabled; tolerate empty)
   - `list_cycles(project_id)` — cycle name → id (tolerate empty)
   - `get_me()` — user id for `owned_by` when creating cycles

   If `modules` or `cycles` features are disabled and the user asked for one, enable via `update_project_features` before proceeding.

---

## Phase 1 — DISCOVER

0. **Read the project SOUL.md first** (if one exists). Scan in this order, use first match: `packages/<pkg>/SOUL.md` (package-centric repos) → `documentation/<project>/SOUL.md` (docs-centric repos where code spans multiple packages — e.g. when the plan's `Source:` points under `documentation/<name>/`) → repo root `SOUL.md` (company-level cascade). If a concern's title or body directly violates a forbidden pattern from the resolved SOUL, the issue should be flagged at creation time (add a `soul-review` label and a comment explaining the conflict). This catches soul-violating work before it enters Backlog, where it's easier to dismiss than to surface. No SOUL.md anywhere ⇒ skip this gate.
1. Read `<plan-path>/00-overview.md` for scope table, dependency graph, and any `Plane tracking` hints (module/cycle suggestions, pre-assigned labels).
2. Glob `<plan-path>/*-concern.md` (also accept `*-concern-*.md` or `NN-*.md`).
3. Parse each concern's frontmatter:
   - `STATUS` (open / in-progress / done / blocked / cancelled)
   - `PRIORITY` (p0 / p1 / p2)
   - `COMPLEXITY` (mechanical / architectural / research)
   - `TOUCHES` (list of file paths)
   - `REPOS` (optional — affected repos for cross-repo concerns)
   - `BLOCKED_BY` (optional — list of sibling concern IDs)
   - `MODE` (`hitl` / `afk`, default `afk`; unrecognized value → treat as `hitl` and warn — fail closed, same rule as concern 01/02's COMPLEXITY/STATUS parse)
4. Parse body: Goal, Approach, Cross-Repo Side Effects, Verify, plus any `PLANE:` line from a prior run (idempotency check).

If a concern already has a `PLANE: <IDENT>-NN` line (any project prefix), **skip it** unless `--force` is passed. That makes re-running the skill safe after the plan gains new concerns. A concern whose `MODE` is flipped after filing only reaches Plane on a subsequent `--force` run — the label/title would otherwise drift silently. This is cosmetic, not a safety hole: `/claim-and-implement`'s pre-flight reads the source doc's `MODE` directly, not the Plane title or label. Still, recommend `--force` to the user right after they flip a `MODE` value, so triage view doesn't lie.

---

## Phase 2 — MAP

For each concern, build the Plane issue payload:

### Title

`MODE: hitl` → append ` [human-review]` to the issue title. This is the enforcement mechanism, not decoration: the omp-squad daemon's only dispatch skip is a title regex — `noAutoDispatchName` (`do not auto-land | human-review | do-not-auto`, in `~/sui/omp-squad/src/plane.ts`) — and the dispatcher (`src/dispatch.ts`) reads no labels at dispatch time. The `hitl` label below is cosmetic triage color; the title marker is what actually stops the fleet from picking up the issue.

### Priority mapping
| Plan PRIORITY | Plane `priority` |
|---|---|
| p0 | `urgent` |
| p1 | `high` |
| p2 | `medium` |
| (none) | `none` |

### State mapping
| Plan STATUS | Plane state |
|---|---|
| open + no BLOCKED_BY | `Todo` |
| open + has BLOCKED_BY | `Backlog` |
| in-progress | `In Progress` |
| done | `Done` |
| blocked | `Backlog` (Plane has no native Blocked state) |
| cancelled | `Cancelled` |

### Labels to attach

Always-applied:
- COMPLEXITY tag → label `mechanical` / `architectural` / `research` (create the label with a muted color if missing).
- `MODE: hitl` → label `hitl` (triage color only — this label is cosmetic, never the enforcement mechanism; see the Title rule above for what actually blocks fleet dispatch).

Component/topic inference (dagon path + keyword heuristics): `references/label-inference-dagon.md`.

**Principle:** only attach a label if the signal is strong. When in doubt, omit — a noisy label dilutes triage. Inference is heuristic; if the user corrects you, add to the concern's frontmatter an explicit `LABELS: [...]` field and it overrides inference next run.

### Dependency handling — REAL `blocked_by` relations (load-bearing for deterministic dispatch)

**Plane HAS a dependency primitive: `blocked_by` work-item relations — USE IT.** The squad daemon's dispatcher reads them (`fetchBlockedBy` in `src/plane.ts`) and **defers an issue while any blocker is still open**. Encoding the plan's dependency graph as real relations is what makes the fleet build concerns *in order* instead of dispatching the whole DAG at once, forking from the same base, and racing/diverging at land. **This is not optional decoration — it is the determinism mechanism.**

For every concern C with a non-empty `BLOCKED_BY` (from the concern frontmatter or the overview "Dependency graph" table), after the work items exist (Phase 3):
- `create_work_item_relation(project_id, work_item_id=C.id, relation_type="blocked_by", issues=[<blocker ids>])` — pass **all** of C's blockers in one call. This handles multi-blocker DAGs natively; no "primary blocker in parent, rest in prose" workaround.
- `parent` is OPTIONAL and for HIERARCHY only (e.g. a `NN.M` sub-concern under its `NN` parent) — never as a dependency stand-in.

Still render a human-readable "Blocked by: …" line in the description for reviewers, but the **relation is the source of truth the dispatcher obeys**. The state mapping below (blocked ⇒ Backlog) is a second guard; the relation is the primary one.

### Description

Render as HTML. Include, in order:
1. `<p><strong>Source:</strong> <code>plan-path/NN-concern.md</code></p>` — always, so issues are traceable back to the plan doc.
2. The concern's Goal section.
3. The Approach section.
4. Cross-Repo Side Effects (if present).
5. Verify (if present).
6. `<p><strong>Blocked by:</strong> ...</p>` (if multiple BLOCKED_BY entries).
7. `<p><strong>Touches:</strong> <code>path1</code>, <code>path2</code>, ...</p>` (from TOUCHES).

Keep it tight. Raw markdown-to-HTML via Claude's rendering is fine — no need for a full pandoc pass.

---

## Phase 3 — CREATE

Look up labels/modules/cycles by name, not by cached ID — IDs are workspace-specific and change across projects; always resolve by name at invocation time.

### Module

1. If `--module <name>` passed → look up (or create) by name.
2. Else if 00-overview.md names a module → use/create it.
3. Else default: module name = plan directory basename (e.g., `plans/hackathon-miami/` → module `Hackathon Miami`).
4. Module description should point back at the plan doc path.

Enable the `modules` project feature via `update_project_features` if it's off.

### Cycle

1. If `--cycle <name>` passed → look up or create (ask user for dates if creating).
2. Else if 00-overview.md names a cycle → use/create it.
3. Else: no cycle.

When creating a cycle, you MUST pass `owned_by` (user id from `get_me()`). Dates go as ISO 8601 (`2026-04-06` style). Cycle status is automatically derived from dates.

### Batch creation

Create all work items in parallel (one `create_work_item` call per concern). Collect the returned IDs in order.

After all are created:
- One `add_work_items_to_module` call with the full ID list (if module chosen).
- One `add_work_items_to_cycle` call with the full ID list (if cycle chosen).

### Dependency relations (MANDATORY — the determinism step)

Resolve each concern's `BLOCKED_BY` (concern numbers) to the work-item IDs created above, then create the relations:
- For each concern C with blockers: `create_work_item_relation(project_id, work_item_id=C.id, relation_type="blocked_by", issues=[<blocker ids>])`.
- These can run sequentially (Plane rate-limits relation POSTs; a 429 would silently drop a relation and let a blocked issue dispatch early).

**Verify before declaring success:** for at least every concern that had blockers, call `list_work_item_relations(project_id, work_item_id=C.id)` and confirm its `blocked_by` array matches the plan. A plan whose `blocked_by` relations don't round-trip is NOT safely dispatchable — the fleet would race the DAG. Report any relation that failed to create.

---

## Phase 4 — BACKFILL

Update the plan docs to reflect what landed in Plane:

1. For each concern, prepend to its body (after frontmatter) or append to its metadata block (substitute the resolved `<IDENT>` and `<workspace>`):
   ```
   PLANE: <IDENT>-NN — https://app.plane.so/<workspace>/browse/<IDENT>-NN/
   ```

2. Update `00-overview.md` with a new section:
   ```markdown
   ## Plane tracking
   - Module: [<Name>](<url>)
   - Cycle: [<Name>](<url>)  <!-- omit if no cycle -->
   - Issues:
     - [01-concern](<url>) — <IDENT>-NN
     - [02-concern](<url>) — <IDENT>-NN+1
     - ...
   ```

   The **Module `<url>` must be the canonical deep link** `https://app.plane.so/<workspace>/projects/<projectId>/modules/<moduleId>/` (the `create_module` response gives you `<moduleId>`; you resolved `<projectId>`/`<workspace>` in pre-flight). The omp-squad daemon reads this exact line — `planeModuleUrlIn` in `src/features.ts` scrapes the first `…/modules/<id>` URL out of the plan dir — so the webui can show **"Module linked"** for skill-filed plans whose module the daemon never created itself. A non-canonical or missing URL means the webui can't link the module back to the plan.

3. Report to the user:
   - Module URL (so they can open the module view)
   - Cycle URL (if applicable)
   - Count of issues created, skipped (already had PLANE: line), failed

---

## Idempotency + re-runs

Re-running the skill on the same plan directory must be safe:
- Concerns with an existing `PLANE:` line are skipped unless `--force`.
- Modules/cycles are looked up by name before create — no duplicates.
- Labels are looked up by name before create.

When the user adds new concerns to an existing plan and re-runs, only the new concerns get created.

When the user closes an issue in Plane and marks STATUS: done in the plan, DO NOT mutate the Plane state — state-of-truth is split: Plane owns open status, plan owns design rationale. Closing an issue manually in Plane is fine; don't sync it back.

---

## --dry-run

Skip all `create_*` and `update_*` calls. Print exactly what would be created:
- Module name (new or existing)
- Cycle name (new or existing)
- Per-concern: title, priority, state, labels, parent (if any)
- Total count of creates / skips

Useful for reviewing inference before committing.

---

## Scope interpretation

| Input | Behavior |
|---|---|
| `<plan-path>` | Full pipeline on that directory |
| `<plan-path> --dry-run` | Print-only; no writes |
| `<plan-path> --module <name>` | Force module (create if missing) |
| `<plan-path> --cycle <name>` | Force cycle (ask for dates if creating) |
| `<plan-path> --force` | Re-create issues for concerns that already have `PLANE:` lines |
| `audit <plan-path>` | Read-only consistency check: list concerns without PLANE: lines, PLANE: lines pointing at deleted issues, issues in Plane that aren't in the plan |

---

## When NOT to use this skill

- For one-off tasks without a plan doc. Use the conversational "file this issue" pattern instead; the doc-less work isn't worth creating a directory for.
- For tracking retros, post-mortems, or closed historical work. That belongs in `MEMORY.md` or `plans/archive/`, not as open Plane issues.
- For design documents that aren't decomposed into concerns yet. Run `/plan` first, then this skill on its output.

---

## Downstream composition

After this skill creates triage-tier Plane issues, **`/promote-issue <IDENT>-NN`** upgrades individual issues from triage-ready (Backlog) to implementation-ready (Todo) by adding the six-field universal task schema (file paths + lines, acceptance test, verification gate, scope, expected/actual, optional reference diff). See `~/.claude/skills/promote-issue/SKILL.md`.

Use cadence (`<IDENT>` = the resolved project identifier, e.g. `OMPSQ`):
1. `/plan` produces `plans/<goal>/`.
2. `/plan-to-plane plans/<goal>/` files them as Backlog triage issues.
3. `/promote-issue <IDENT>-NN` upgrades one issue at a time when it's next up for implementation.
4. `/claim-and-implement <IDENT>-NN` picks up the tier-2 issue and does the work.

## Reference

- `reference_plane_mcp.md` in auto-memory — canonical Plane MCP setup notes.
- `~/.claude/skills/plan/SKILL.md` — upstream source of the concern file format this skill consumes.
- `~/.claude/skills/promote-issue/SKILL.md` — the tier-2 promotion companion skill.
- `https://app.plane.so/inkwell-finance/` — workspace base URL; all issue/module/cycle URLs are derived from this.
