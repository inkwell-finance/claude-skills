---
name: sync-plans
description: Pull Plane state back into plan-doc STATUS lines so the WIP counter reflects reality. For every concern with a `PLANE: <IDENT>-NN` pointer, fetch the Plane issue's current state via MCP and rewrite the concern's STATUS line if it drifted. Closes the bidirectional gap that /plan-to-plane deliberately left open. Use before /wip triage so the easy closures auto-resolve.
argument-hint: "[--dry-run] [--plan <plan-name>] [--repo <path>]"
---

# sync-plans

One-way sync: **Plane → plan doc**. Plan docs are cache; Plane is truth for state. This skill refreshes the cache.

```
SCAN → FETCH → DIFF → WRITE
```

## Why this exists

`/plan-to-plane` writes a forward pointer (`PLANE: DAGON-NN — url`) into every concern it files. But the reverse never fires: when you close a Plane issue, the plan doc's `STATUS: open` goes stale and the WIP counter over-reports open work. This skill closes that gap.

The design rule from `/plan-to-plane` is: **Plane is source of truth for open-status; plan doc is source of truth for design rationale.** That rule still holds — this skill only syncs STATUS, nothing else. Design rationale, approach, verification — none of that moves.

## Pre-flight

1. **Plane resolution + MCP.** Per `reference_plane_mcp.md` (auto-memory, the owner of this contract): `.plane.json` → `PLANE_PROJECT_MAP`/`PLANE_PROJECT_ID` → `list_projects` → ask; MCP only, never REST curl fallback.
2. **Scanner available.** `~/.claude/skills/wip/lib/scan.py` must exist. It's how we enumerate concerns with Plane pointers.
3. **Repo root.** Default to cwd. User can override with `--repo <path>`.

## Phase 1 — SCAN

Run the scanner in JSON mode:

```bash
python3 ~/.claude/skills/wip/lib/scan.py <repo-root> --format json
```

Filter to concerns with `plane_id != null`. Group by project prefix (the `<IDENT>-` in each `PLANE: <IDENT>-NN`, whatever projects appear) so we batch MCP calls per-project.

If `--plan <name>` is passed, narrow to concerns inside that plan only.

If zero concerns have `PLANE:` pointers, report "no promoted concerns — nothing to sync" and exit. This is the normal state for a repo that hasn't run `/plan-to-plane` yet.

## Phase 2 — FETCH

For each Plane project with concerns to sync, fetch current state in batches.

The MCP tool `mcp__plane__list_work_items` supports filtering by project_id. Pull all work items in the project that might match our pointers, with `expand=state`. Cache the project's state name map (state UUID → human name) from `mcp__plane__list_states(project_id)`.

Build a lookup: `{ "DAGON-9": { "state_name": "Todo", "completed_at": null, "archived_at": null } }`.

Prefer a single batch retrieve per project over per-issue calls — for 30 concerns across 3 plans, that's 1 `list_work_items` + 1 `list_states` per project, not 30 individual retrieves.

Resolving a `<PREFIX>-NN` pointer to a project id: the `<PREFIX>` is the Plane project `identifier` — resolve it once per run via the pre-flight #1 chain and cache the prefix → `projectId` + state map for the run.

## Phase 3 — DIFF

Map Plane state → plan STATUS:

| Plane state_name | `completed_at` | plan STATUS |
|---|---|---|
| Backlog | — | `open` |
| Todo | — | `open` |
| In Progress | — | `in-progress` |
| Done / Completed | set | `done` — never `closed`: `/plan-to-plane` and `/claim-and-implement` parse `done` only (the WIP scanner tolerates both, the siblings don't) |
| Cancelled | set | `cancelled` |
| *missing* (404 — issue deleted) | — | leave unchanged; **warn loudly** |

If the plan doc's current STATUS matches the computed value, skip. If it differs, enqueue a rewrite.

Special cases:
- `archived_at` set → treat as `cancelled`.
- Pointer references an issue that doesn't exist anymore → do NOT flip to cancelled silently; report to the user as `stale-pointer` and let them decide. The issue may have been moved, merged, or deleted manually.
- STATUS is `blocked` locally but Plane says `Todo` — this is a local-only annotation. Keep `blocked`, don't downgrade. `blocked` is richer information than Plane's state vocabulary supports. But flag it to the user as a divergence worth confirming.

## Phase 4 — WRITE

For each concern that needs updating:

1. Read the concern file.
2. Rewrite the STATUS line in place. Support both conventions:
   - Canonical: replace `^STATUS:\s*\w[\w-]*` with `STATUS: <new>`.
   - Bold markdown: replace `^\*\*Status:\*\*\s*\w[\w-]*` with `**Status:** <new>`.
3. Append a sync trail comment at the bottom of the file (before any existing trailer) so the history is inspectable later:
   ```
   <!-- sync-plans: STATUS open → done via PLANE DAGON-9 on 2026-04-19 (Plane state: Done) -->
   ```
4. Write back.

If `--dry-run` is set, skip step 4 and instead print a diff-style preview:
```
packages/dagon/plans/dagon-concern-30-account-id-binding.md:
  STATUS: open  →  done
  (plane DAGON-9: Done, completed_at 2026-04-19)
```

## Phase 5 — REPORT

Refer by name in this section: wrap ids in the issue's title in any prose shown to the user, e.g. `DAGON-9 "Account id binding"`, not a bare id. This is human-facing output only — the sync trail comment (Phase 4) and `PLANE:` frontmatter are machine-read and stay bare; don't title-wrap those.

After writing, emit a summary:

```
Synced 12 concerns across 2 plans.
  4 open → done
  2 open → in-progress
  1 open → cancelled
  5 unchanged
Divergences needing attention:
  - packages/dagon/plans/dagon-concern-21-foo.md: Foo bar (DAGON-21) is STATUS=blocked locally but Plane is Todo (keep blocked? [y/N])
  - plans/lika-phase4/03-transaction-history.md: PLANE points to Transaction history (LIKA-7), which doesn't exist in Plane. Remove pointer? [y/N]
```

The divergence prompts are interactive; don't mutate until the user confirms.

## Composition

Run before `/wip triage` and before `/plan` Phase 0; idempotent, safe to schedule.

## --dry-run

Report what would change. Never writes files, never calls Plane's state-mutating MCP tools (this skill doesn't mutate Plane anyway — it's read-only against Plane — but the flag still suppresses the disk writes).

## When NOT to use

- On a repo with no `PLANE:` pointers in any concern. The skill will run, find nothing, and exit — but you didn't need to call it. Run it once after the first `/plan-to-plane` invocation.
- When Plane is down / MCP is disconnected. Wait; don't fall back to a REST scrape.
- To sync metadata other than state (priority, labels, module). That's out of scope — this skill is exclusively about STATUS. Other sync surfaces can be their own skills.

## Reference

- `~/.claude/skills/plan-to-plane/SKILL.md` — writes the `PLANE:` pointer this skill reads. Source-of-truth rule defined there.
- `~/.claude/skills/wip/SKILL.md` — the WIP counter that benefits from fresh STATUS; run this first, then `/wip triage` for the leftovers.
- `reference_plane_mcp.md` in auto-memory — MCP setup and project IDs.
