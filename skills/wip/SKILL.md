---
name: wip
description: Surface in-flight plan work so it's visible, rankable, and finishable — scans every plans/ directory under the current repo, aggregates concern STATUS counts per plan, and shows what's been sitting open the longest. Use when the user asks "what's in flight", "what plans are open", "what should I finish", wants to resume abandoned work, or needs a WIP snapshot before starting something new. Also invoked as a pre-flight inside /plan to force the "should I start another one?" conversation.
argument-hint: "[resume | triage <plan> | --format summary|json | --rank]"
---

# wip

A WIP counter for plan docs. The problem it solves: `/plan` is cheap to start and invisible to finish, so plans pile up. This skill makes the pile visible — one number, ranked list, next actionable concern — so the pile can actually be worked down instead of forgotten.

```
SCAN → RANK → ACT
```

## Why this exists

`plans/` directories accumulate for months with `STATUS: open` written at creation and never updated — starting a 35th plan feels as cheap as the first, and half-done plans calcify.
This skill makes the pile one visible ranked number: stale work surfaces by age, `/wip resume` hands over the most-worth-finishing concern, `/wip triage` fixes the STATUS-drift root cause.

## Scope interpretation

| Input | Behavior |
|---|---|
| `/wip` | Default: summary listing of every plans dir under the current repo, ranked by oldest-with-open-work |
| `/wip resume` | Pick the top-ranked plan and surface its next unblocked concern as a concrete action |
| `/wip triage <plan-name>` | Interactive pass through a plan's open concerns; classify each as done / still-open / abandoned; write back STATUS |
| `/wip --format json` | Emit the raw scan output for composition with other skills |
| `/wip --rank` | (Default in summary mode) Sort by the finish-worth heuristic |
| `/wip --include-archive` | Scan `plans/archive/` too — usually omit |

## Phase 1 — SCAN

Run the scanner:

```bash
python3 ~/.claude/skills/wip/lib/scan.py <repo-root> --format summary --rank
```

`<repo-root>` is the top of the working repo (usually the cwd unless the user is in a sub-package). The scanner handles two formats transparently:

1. **Canonical `/plan` directories:** `plans/<name>/NN-concern.md` with `STATUS: <state>` lines.
2. **Flat dagon-style files:** `packages/dagon/plans/concern-*.md` with `**Status:** <state>` markdown-bold lines.

It reads, per concern:
- `STATUS` (canonical or bold)
- `PRIORITY` (optional)
- `MODE` (`hitl` | `afk`; absent defaults to `afk`; an unrecognized value fails closed to `hitl` plus a warning — a typo must never unlock autonomous dispatch)
- `PLANE:` line (the pointer written by `/plan-to-plane` — absent means the concern hasn't been promoted).

It also reads each plan dir's `00-overview.md` once (not skipped, despite not being a concern file) for two aggregate signals: `has_fog` (a `## Not yet specified` section with a real bullet, not just the canonical `- (none)` marker) and `design_pending` (`## Notes` containing `DECOMPOSE: pending`). A dir with either signal stays in the scan even with zero concern files.

Skipped as concern files (but `00-overview.md` is still read for the two signals above): `DESIGN.md`, `CEO-PLAN.md`, any `.md` with no STATUS at all (those are design / landscape / narrative docs, not concerns).

## Phase 2 — RANK

The scanner's `--rank` flag sorts by the "most worth finishing" heuristic:

1. **Plans with open concerns first.** Clean plans sink.
2. **More open concerns first** — these aren't the cheapest, they're the most valuable to close out (a half-done plan with 18 open concerns represents more reclaimable work than one with 2).
3. **Oldest-activity first** — stale plans surface before recent ones, because they're the ones actually getting lost.
4. **More-promoted first** (tiebreak) — plans with a lot of `PLANE:` pointers are closer to the agent-handoff line; finishing them is cheaper than starting equivalent work from scratch.

## Phase 3 — ACT

Based on the sub-command:

### `/wip` (default: read-only summary)

Print the ranked table to the user. Example:

```
# WIP under /home/lars/sui/inkwell
  47 plans, 40 with open concerns
  299 open concerns, 53 closed, 0 promoted to Plane
  6 hitl — waiting on you

plan                                 open  closed  plane      oldest
---------------------------------------------------------------------
dagon:post-research-roadmap            18       4      0  2026-04-13  (3 hitl — waiting on you)
inkwell:lika-remediation               18       0      0  2026-04-17  (fog present)
inkwell:venue-integration              16       0      0  2026-03-26  (design pending)
...
```

The scanner emits `hitl_open`, `has_fog`, and `design_pending` per plan; the summary turns these into the totals-line "N hitl — waiting on you" and the trailing per-plan notes above.

Then suggest concrete next steps:
- "`/wip resume <plan-name>` to pick up the oldest unblocked concern in that plan"
- "`/wip triage <plan-name>` to close the concerns that are already done (most of the 0-closed plans above are probably partly-finished, just unmaintained)"
- "`/sync-plans` to pull Plane state and backfill STATUS for concerns that have been promoted"

### `/wip resume [<plan-name>]`

1. If no plan-name given, use the top-ranked plan from the scanner output.
2. Read its `00-overview.md` (if present) for the dependency graph, and orient from `## Decisions so far` rather than re-reading every closed concern file — zoom into an individual concern's body only if the index row doesn't answer the question at hand.
3. Load all concerns, filter for `status == open`, no unsatisfied `BLOCKED_BY`, and `MODE` not `hitl`. HITL concerns are never candidates here — list them separately as **waiting on you** (title-wrapped, e.g. `Pyth threshold validation`, never a bare filename or NN-number) and don't hand them to an agent.
4. Sort by concern number (NN- prefix) — plan authors order by dependency, so lower NN means closer to root.
5. Pick the first one. Read its body.
6. Present to the user: title, Goal section, Approach section summary (≤100 words), verification gate.
7. Offer: "Resume this? I'll hand it off as the next task." If yes, begin the work with the concern as the scope boundary.

If the user declines, surface the next concern in the list. If they decline everything, suggest `/wip triage <plan>` instead — maybe the plan is done and just needs closing out. If every remaining concern is `hitl`, say so plainly ("N concerns left, all waiting on you") instead of falling through to picking one anyway.

### `/wip triage <plan-name>`

The cleanup loop. For each open concern in the plan, in order:

1. Show: title, STATUS, PRIORITY, TOUCHES, one-paragraph Goal.
2. Ask the user: `done / open / blocked / abandoned / ruled-out / skip`.
3. Before any flip, verify `done` claims: grep the TOUCHES files for evidence the work shipped (function exists? file exists?); if evidence doesn't match, warn the user and confirm before recording. STATUS is always written as `done`, never `closed` — `/plan-to-plane` and `/claim-and-implement` parse `done` only; `apply_audit.py` already writes `done`.
4. Collect the verdicts into an audit JSON and apply the flips with:
   ```bash
   python3 ~/.claude/skills/wip/lib/apply_audit.py <audit.json> [--confidence high] [--dry-run]
   ```
   Audit-JSON input (full contract in `apply_audit.py`'s docstring): a JSON array of items with
   `path` (concern file), `current_status`, `recommended_status` (`done` / `open` / `blocked` / `cancelled`),
   `confidence` (`high` / `medium` / `low` — only `high` applies by default), `evidence` (short citation),
   and `resolution` (one-line note or null). The script rewrites the STATUS line, appends/updates a
   `## Resolution` section for done/cancelled items, and refuses any file whose STATUS line drifted from `current_status`.

After the concern loop, walk fog: if `00-overview.md`'s `## Not yet specified` has real bullets (not the canonical `- (none)` marker), take each in turn and ask the user to resolve it:
- **graduate**: the question is now phrasable precisely — create a numbered concern for it and remove the bullet.
- **still-fog**: leave the bullet where it is; it isn't ripe yet.
- **rule out**: move it to `## Out of scope` with the ruling-out rationale, same ledger a ruled-out concern uses.

After both loops, re-run the scanner summary so the user sees the updated numbers.

**Important:** this mutates plan docs. Always show the user the diff of each STATUS change and each `00-overview.md` edit before writing. Batch the writes so a single "yes" can approve a whole plan's triage.

## Key behaviors

- **Read-only by default.** `/wip` and `/wip resume` never mutate plan docs. Only `/wip triage` writes.
- **Evidence-based closure.** In triage mode, "done" claims must be grep-verifiable against TOUCHES before flipping STATUS — otherwise the user lies to themselves and the pile regrows.
- **Don't delete plans.** Even a fully-closed plan stays on disk as design record. Move to `plans/archive/` only if the user explicitly says "archive this."
- **Stale is a feature.** A plan untouched for 60 days is valuable signal, not noise — surface it. The point is to force the "still relevant?" conversation.
- **No opinion on what to work on.** Rank is a heuristic, not a mandate. The user picks; this skill just makes the options legible.
- **Refer by name.** In human-facing prose — the hitl notes in a summary, resume's waiting-on-you list, triage prompts — wrap a concern reference in its title, never a bare filename or NN-number. Machine-read surfaces (`STATUS:`/`MODE:`/`PLANE:` frontmatter, file paths passed to other tools) are exempt.

## Scanner contract (for composing skills)

`~/.claude/skills/wip/lib/scan.py <dir> --format json` — the keys consumers actually read:

```json
{
  "plans": [
    {
      "name": "lika-phase4",
      "path": "/abs/path/plans/lika-phase4",
      "open_count": 11,
      "hitl_open": 2,
      "concerns": [ { "plane_id": "DAGON-9" | null, "mode": "afk" | "hitl", ... }, ... ]
    }
  ]
}
```

`scan.py`'s docstring is the full contract. Stable keys; any future field additions will be additive.

## When NOT to use

- As a substitute for actual work. `/wip` visualises; it doesn't finish. The list exists so the user can pick one and `/wip resume` into it.
- On a repo with no `plans/` directories. It'll cleanly return "0 plans" and exit; no harm, but also no value.

## Reference

- `~/.claude/skills/plan/SKILL.md` — upstream source of the concern file format this scanner reads.
- `~/.claude/skills/plan-to-plane/SKILL.md` — writes the `PLANE:` pointer that `/sync-plans` later reads.
- `~/.claude/skills/sync-plans/SKILL.md` — companion: pulls Plane state back into plan doc STATUS.
- `~/.claude/skills/wip/lib/scan.py` — the scanner. Invoke directly for composition.
