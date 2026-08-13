---
name: squad
description: Drive work to done with the omp-squad daemon fleet ONLY — every unit runs in its own isolated git worktree and lands via a proven merge, so parallel agents never collide, clobber, or delete each other's code. Use when the user says "squad it", "/squad", or "run the fleet", or wants maximum autonomous throughput on a build/refactor/migration. Decompose into independently landable units, dispatch each to a worktree-isolated agent (build → verify → land → resolve hands-free), and supervise by exception. NEVER edit the shared working tree with parallel in-harness subagents.
argument-hint: "<goal | plans/<name> | plane issues>"
---

# Squad

Drive work to **done** with the **omp-squad daemon fleet — and ONLY the daemon fleet**. Every unit of work runs in its **own `git worktree`**, builds → verifies → **lands via a proven merge**. "Squad it" / "send it to the fleet" means: stop editing files yourself, decompose into landable units, dispatch them to isolated agents, and supervise by exception.

```
PRE-FLIGHT → DECOMPOSE INTO LANDABLE UNITS → DISPATCH TO THE FLEET → SUPERVISE BY EXCEPTION → LAND → CLOSE
```

## THE RULE (read first, never break)

> **All code/behavior changes go through fleet agents in their own worktrees. NEVER fan work out as parallel in-harness `task`/`quick_task` subagents that edit files.**

In-harness subagents all share **one** working tree — concurrent edits there cause exactly the **merge conflicts, lost edits, and deleted code** this skill exists to prevent. The daemon fleet isolates each agent in a separate worktree+branch and only integrates through a **verified, conflict-resolved land**, so two agents physically cannot stomp each other.

- ✅ Read-only `task`/`explore` for *investigation/decomposition* is fine (they don't edit).
- ✅ The orchestrator (you) edits only **orchestration metadata** in the main tree — plan `STATUS`, `00-overview.md` bookkeeping — never the source under change.
- ❌ No parallel subagents editing source. No "I'll just do this one file myself" mid-fan-out. If it changes code, it's a **fleet agent in a worktree**.

This skill composes with the others: `/plan` decomposes, `/wip` is the pre-flight, `/plan-to-plane` files the units as Plane issues for auto-dispatch, `/claim-and-implement` is the single-issue leg. `/squad` is the **fleet dispatch + autonomy + supervision** layer.

---

## 0. Pre-flight (always)

1. **WIP check** — don't pile on:
   ```bash
   python3 ~/.claude/skills/wip/lib/scan.py <repo-root> --format summary --rank
   ```
   Open concerns exist → surface them, confirm (proceed / resume / triage) first.
2. **Scope** — one sentence for "done" + the **acceptance command** that proves it (exits 0). Every unit you dispatch carries its own acceptance gate, so this is required, not optional.
3. **Decompose into LANDABLE UNITS** (next section). Non-trivial → chain `/plan` first (EXPLORE → adversarial DESIGN → DECOMPOSE into `plans/<name>/NN-concern.md` with `BLOCKED_BY` + `TOUCHES`). If `/plan` already ran, start from its concerns.

---

## 1. Decompose into independently landable units

The fleet's safety comes from isolation, so the decomposition must respect it:

- **Each unit = one worktree agent = one branch that lands cleanly on its own.** A unit is a feature/bug/concern that builds and passes its acceptance gate in isolation.
- **Shared-file / dependency coupling is handled by ORDERING, not by concurrent edits.** If unit B depends on A's code (shared type, new module), **dispatch A first, let it land, then dispatch B off the updated main.** Two units that heavily share a file are either (a) sequenced this way, or (b) **merged into one unit** for one agent. They are NEVER run as two agents editing the same file in parallel.
- **Independent units run concurrently** — disjoint files, separate features, separate Plane issues — because their worktrees can't collide and `landAgent` serializes the merges per repo.
- **Conflicts at land time are expected and handled** (the resolve step), not avoided by serializing everything: only *dependency* edges force ordering, not mere file overlap that the resolver can combine.
- **A `MODE: hitl` concern is never a fleet unit.** On Plane it carries a `[human-review]` title marker (the daemon's actual skip signal — see §7) and a `hitl` label (triage color only). It needs a human decision, not a worktree agent — park it and say so in the dispatch report rather than dispatching or waiting it out.

Produce a small dispatch plan: which units go now (no unmet dependency), which wait on a land.

---

## 2. Ensure a daemon

- Already running → use it (`omp-squad list`).
- Start one: `omp-squad up --no-tui` (web at `:7878`). One daemon per state dir (single-writer lock).
- **One terminal per daemon — never drive/monitor the same daemon from two terminals.** A second terminal's orphan-reaper garbage-collects in-flight worktrees AND branches, silently vaporizing uncommitted agent work; it presents as "daemon instability"/SIGTERM. Before reaper-prone integration work (big hand-merges), confirm no other terminal is attached, or do the merge in a scratchpad worktree off the daemon with resolutions committed immediately and incrementally.
- **The observer loop (`OMP_SQUAD_OBSERVE`) auto-files and dispatches its own agents.** An agent you didn't dispatch is usually this, not a bug — close its tracking issue at the source rather than re-investigating.
- **Monitor via the daemon's JSON roster API, not the text roster** — the text view misparses into duplicate columns and spams monitors.
- **Throwaway / isolated fleet** (never collide with the operator's real daemon, lock, or port):
  ```bash
  OMP_SQUAD_STATE_DIR=/tmp/squad-<name> OMP_SQUAD_PORT=7991 omp-squad up --no-tui
  ```

---

## 3. Turn the autonomy all the way up (the dials)

All ON by default — *that is the point*. List them so you know what's live and can scope down per run.

| Env | Effect (default ON unless noted) |
|---|---|
| `OMP_SQUAD_AUTODISPATCH` | Plane issue → routed agent on a timer (`DISPATCH_INTERVAL_MS`=60000, `DISPATCH_MAX`=3). On when Plane is configured. |
| `OMP_SQUAD_AUTODRIVE` | Self-healing tick: auto-land green agents, self-heal red gates (retry/hold/escalate by `REPAIR_BUDGET`=3), trip one `CATASTROPHE:` on budget exhaustion, drain the park queue. |
| `OMP_SQUAD_AUTOLAND` | A green workflow/verify run lands its own branch. `LAND_CONFIRM`=1 ⇒ green only marks **✓ ready** (you tap Land). |
| `OMP_SQUAD_AUTORESOLVE` | At land, rebase-resolve conflicts, then **prove** (full verify gate **+** independent reviewer) before keeping — else roll back. This is how parallel branches integrate without losing code. |
| `OMP_SQUAD_AUTOSUPERVISE` | Auto-answer **low-risk** prompts (`AUTOSUPERVISE_BUDGET`=5/agent); skips destructive patterns + host-tool calls; every answer audited. |
| `OMP_SQUAD_AUTOCLOSE` | Mark a tracking Plane issue done once its branch lands. |
| `OMP_SQUAD_OBSERVE` | Self-audit loop: detect gaps (red gate on main, unreaped survivors, stale-Done, land hazards), file fix-issues (deduped). |
| `OMP_SQUAD_MAX_WIP` (6) · `MAX_AGENTS` (2×WIP, floor 12) · `QUEUE_ON_FULL` | Concurrency ceiling + a FIFO park queue so a backlog can't storm the host. |
| `OMP_SQUAD_LLM_ROUTER=1` | Classify intake with a one-shot fast-model call instead of heuristics. |

With AUTODISPATCH + AUTODRIVE + AUTOLAND + AUTORESOLVE + AUTOSUPERVISE on, the loop closes end-to-end: **intake → route → build → verify → land → resolve-on-conflict → close**, human-needed only for destructive gates and unprovable resolutions.

---

## 4. Dispatch the work

Every unit is a fleet agent. Always attach an acceptance gate so "agent says done" becomes "done **and** green".

**Standing dispatch brief** — bake these into every unit's task line; each was learned from repeated per-unit friction:

- **"Commit your work in logical groups before going idle."** Workflow wrappers loop on `verify` and otherwise sit idle with a dirty tree, forcing a manual commit round-trip per unit.
- **The land path itself now runs a conflict-marker gate automatically (#330, `OMP_SQUAD_CONFLICT_MARKER_GATE`, ON by default)** — a textual scan of a branch's ADDED lines refuses to land any file (`.md`/`.json`/`.txt` included) that still carries a live `<<<<<<<`/`=======`/`>>>>>>>` line, distinct from git's own structural conflict check and from a typecheck/test acceptance gate that a marker-laden doc or config file can pass unnoticed. It runs on the ordinary path AND on AUTORESOLVE's rebase-resolved output, so a resolver that reports success while leaving debris behind is caught before it reaches main. "Green with markers" is now structurally impossible for THIS daemon's own land, without hand-rolling anything into `--verify`. If you're driving a unit's acceptance command against a DIFFERENT land pipeline that lacks this gate, keep baking an equivalent grep into `--verify` (e.g. `! grep -rn '^<<<<<<< ' --include='*' src/`).
- **Independent fixes (security, perf) base on `origin/main`**, not the integration stack, so they merge on their own instead of queueing behind a long PR chain.

- One unit, intake routes it (verify-loop / plan+approval / fan-out / plain):
  ```bash
  omp-squad add <repo> --name <slug> --task "<one natural-language line>" \
    --verify "<acceptance cmd, exits 0>"
  ```
- Reviewable process graph instead of free text: `--workflow workflows/plan-implement/workflow.fabro`.
- Several approaches in parallel: a `--workflow` fan-out (one steerable agent per branch, each its own worktree).
- Untrusted code off the host: `--sandbox <image>`.
- **Tracked work (preferred at scale):** `/plan-to-plane` files the units as labeled Plane issues; **auto-dispatch pulls them in** — nobody types the line. `/claim-and-implement` is the single-issue end-to-end leg.
- **Dependent units:** dispatch the blocker, **wait for it to land** (watch Race/Features or `omp-squad list`), then dispatch the dependent off updated main. Independent units: dispatch together.

---

## 5. Supervise by exception

- Command center surfaces: **Queue** (every blocked/errored agent, answerable in place, oldest-first), **Race** (per-agent pipeline position — who's stalled), **Features** (lifecycle), **Audit** (who did what). The PWA pushes a notification the moment an agent needs a human.
- **Answer every "status" ask via `/fleet-status`** — it owns the three-bucket ledger format.
- Answer/steer from CLI (`omp-squad prompt <id> "<msg>"`) or the web.
- You watch and unblock; you do **not** hand-edit the code under change.

---

## 6. Land (how the fleet stays collision-free)

- Green branches **auto-land** (`landAgent`: ff when it can, merge commit when diverged, **serialized per-repo** so two lands never corrupt the index). With `LAND_CONFIRM`, green only marks **✓ ready** and you tap Land.
- `main` moved under a branch → **conflict**, handled, not feared:
  - **`OMP_SQUAD_AUTORESOLVE`** rebases + resolves per file, then **proves** (full verify gate **+** independent reviewer pass) before keeping — any failing step **rolls main back**. An unproven resolution is never kept.
  - Or the bundled **`resolve-conflict` workflow** (merge → *combine both sides, keep the feature AND main's change* → verify-gate → bounded fixup) — reviewable on the branch before main ever moves.
- A successful land **closes the tracking Plane issue** (idempotent, best-effort).
- The worktree is the blast radius: nothing reaches main except a verified, conflict-resolved merge — so no agent deletes or clobbers another's code.

---

## 7. Guardrails (hard rules)

- **Process control:** NEVER `pkill`/`killall`, NEVER kill by numeric PID, NEVER `SIGKILL`/`kill -9` — the squad guardrail blocks these and they can take down the operator's daemon + sibling agents. Stop **your own** background processes with a **job spec** (`kill %1`, `kill $!`); a daemon you started exits on **SIGINT** (`kill -INT %1`), not SIGTERM. One job per `kill`.
- **Isolation for any test/demo daemon:** separate `OMP_SQUAD_STATE_DIR` + non-default `--port`; tear it down with SIGINT + `rm -rf` the temp dir.
- **Don't spend tokens to prove plumbing:** seed state on disk / use a committed in-process test instead of running real model agents for a smoke. Reserve real-agent runs for genuine end-to-end work.
- **Respect edit leases** and the operator's concurrent edits — never clobber; the fleet's worktrees already keep your dispatched work off the operator's tree.
- **`cd` to a stable repo root before any commit/dispatch command** — worktree teardown yanks the shell's cwd (`getcwd cannot access`) and can silently drop the dispatch. Never run land-adjacent commands from inside a worktree that another process may remove.
- **Don't trust AUTORESOLVE on non-trivial conflicts** — it has produced rejected merges and rolled main back (once eating a completed land). For real divergence, hand-rebase in a scratchpad worktree and land through the verify gate.
- **Verification ≠ running the project:** typecheck + tests are expected; `dev`/`build`/booting the daemon are deliberate acts.
- **The daemon's only per-issue dispatch skip is a title regex, not a label.** `noAutoDispatchName` (`~/sui/omp-squad/src/plane.ts`) matches `do not auto-land | human-review | do-not-auto` against the issue title; it reads **no labels** at dispatch. The `[human-review]` suffix `/plan-to-plane` writes into the title is therefore the real enforcement; the `hitl` label is triage color and does nothing to keep the fleet off an issue. Never rely on the label alone — check the title marker.

---

## 8. Verify (non-negotiable)

- **Per unit:** the agent's own `--verify` acceptance gate must be green before its branch lands; the resolver's verify+reviewer pass gates any conflict resolution.
- **At the end:** confirm every dispatched unit landed (or is intentionally parked); a full typecheck + test run on main after the lands; for user-facing/integrated behavior, a **live smoke** (curl the endpoint / browser the view) or a committed integration test — build/typecheck alone never proves an integration.
- Tests deterministic, zero-token; one runnable check per non-trivial unit.

---

## 9. Close (the sink — never skip)

- **Update every unit's STATUS** (`closed` landed / `deferred` with reason / `cancelled`) + a one-line `## Resolution` citing the evidence (landed SHA / gate green / live smoke).
- **Update `00-overview.md`**; **re-run the WIP scanner** — the plan drops off the open list.
- **Ship docs with behavior** (AGENTS.md): changed flags/env/endpoints/UI → README + `docs/` / docs-site, ideally as part of a unit's worktree+land.
- **Tear down** any test daemon (SIGINT via `%job`) + temp dirs.
- **Plane-filed?** Don't mutate Plane from here; recommend `/sync-plans` if Plane may be ahead.

---

## 10. Output contract (what to report)

- The dispatch plan: units, which ran concurrently, which were sequenced behind a land, and why.
- Per-unit outcome: agent id, acceptance gate result, **landed / parked / escalated**.
- What shipped vs. **deferred** (with reason — never silently shrink scope).
- Verification evidence: lands confirmed, post-land typecheck/test counts, any live smoke.
- Anything that needed a human (destructive gate / unprovable resolution) and how it resolved.
- Remaining follow-ons, offered, not buried.

---

## Scope interpretation

| Input | Behavior |
|---|---|
| `squad it <goal>` / `/squad <goal>` | Full pipeline: pre-flight → decompose into landable units → ensure daemon → dispatch → supervise → land → close |
| `/squad plans/<name>` | Dispatch the plan's concerns as fleet units (respecting `BLOCKED_BY` ordering) |
| "send it to the fleet" | Same — the daemon fleet is the only path |
| `/squad` (bare, mid-effort) | Resume: read live roster + plan, dispatch the next unblocked units, unblock the Queue |
| "squad it" on a single small change | One fleet agent with a `--verify` gate (still isolated + landed) — or, if truly trivial, say so and just do it directly |

## Anti-patterns

- Editing the feature code yourself mid-dispatch "to save a hop" — it bypasses isolation + the verified land.
- Dispatching dependent units in parallel instead of sequencing the dependent one behind the blocker's land.
- Adding fleet ceremony to a genuinely one-line change.
- Dispatching a `hitl` unit to the fleet (or stripping its `[human-review]` title marker to make it dispatchable) — the label was never load-bearing; the title marker is.
