---
name: claim-and-implement
description: Pick up a fully promoted Plane issue (Tier-1 + Tier-2 body, state=Todo) and execute it end-to-end — claim, parse schema, run baseline acceptance test, implement within the declared scope, run the verification gate, re-run the acceptance test, commit in logical groups, close the Plane issue, update plan-doc STATUS, and record any non-obvious lesson to auto-memory. Third leg of the plan → plan-to-plane → promote-issue → claim-and-implement pipeline. One issue at a time.
argument-hint: "<IDENT-NN> [--dry-run] [--resume] [--scope-audit-only]"
---

# claim-and-implement

The last mile. `/plan` decides what matters; `/plan-to-plane` puts it on the board; `/promote-issue` makes it agent-legible. This skill does the work. If the other three skills' output is well-formed, this skill should look boring — a sequence of deterministic gates around a single judgement-heavy Phase (IMPLEMENT). When the output is not well-formed, this skill refuses to paper over the gap and surfaces the design debt instead.

```
PRE-FLIGHT → CLAIM → PARSE → BASELINE → IMPLEMENT → VERIFY → ACCEPT → COMMIT → CLOSE
```

## Why this exists

Claiming a ticket, doing the work, updating the board, closing the loop — the mechanical bookkeeping around implementation routinely eats more attention than the code. Humans forget one of the four closure steps 80% of the time; agents forget all four unless instructed. This skill makes the bookkeeping a checklist, so the only live judgement is "is the code right?" Everything else is a gate.

The flow also enforces two invariants that humans tend to violate under time pressure:

1. **Baseline before build.** The acceptance test MUST fail before the fix. If it already passes, the work is already done — investigate, don't implement. (The real-world shape: an earlier PR accidentally closed the concern; re-implementing collides and corrupts state.)
2. **Scope boundary is law.** If a necessary change lies outside the declared `ALLOWED` paths, file a new concern, don't silently expand. Silent scope creep is how one-hour tickets become four-hour tickets that fail review for "touches too much."

## Expected invariant (aspirational, not yet battle-tested)

The skill is new. The invariant it MUST hold is: *running it on a well-promoted issue should be indistinguishable from a diligent senior engineer working the ticket*. Not faster — indistinguishable in shape. If, six runs in, the output looks like "agent did the thing but missed the hotspot migration" or "agent shipped but didn't update 00-overview.md," those are calibration bugs — file them into this skill, don't normalise them.

## Pre-flight

1. **Plane resolution + MCP.** Per `reference_plane_mcp.md` (auto-memory, the owner of this contract): `.plane.json` → `PLANE_PROJECT_MAP`/`PLANE_PROJECT_ID` → `list_projects` → ask; MCP only, never REST curl fallback.

2. **Issue identifier parsed.** Accept any `<IDENT>-NN` (the prefix is the Plane project identifier). Resolve to `work_item_id` via `retrieve_work_item_by_identifier`. Cache `sequence_id`, `state`, `labels`, `parent`, `assignees`, `description_html`.

3. **Cache project metadata** in one parallel MCP batch:
   - `list_states(project_id)` — resolve `In Progress` and `Done` state uuids.
   - `list_labels(project_id)` — for `soul-review` / `scope-creep` / `blocked` label application.
   - `get_me()` — user uuid for `assignees` and claim-comment attribution.

4. **State gate.** Issue state MUST be `Todo`. If `Backlog` → refuse and tell the user to run `/promote-issue` first. If `In Progress` → refuse unless `--resume` is passed (someone else — possibly you in a prior session — already claimed). If `Done` / `Cancelled` → refuse and report already closed.

5. **Body gate.** `description_html` MUST contain BOTH `<h2>Tier-1 origin &amp; research context</h2>` AND `<h2>Tier-2 implementation context</h2>`. If only Tier-2 exists, refuse with "run `/promote-issue --force` to backfill Tier-1 before claiming." If neither, refuse and direct to `/promote-issue`.

6. **HITL gate (fail closed).** Check all three signals for a human-in-the-loop marker:
   - Title contains `[human-review]`.
   - Labels include `hitl`.
   - The source plan doc — peek the `<em>Source plan: <code>...</code></em>` line in `description_html` now, PARSE re-reads it in full later — has a `MODE:` line. `MODE: hitl`, or any value other than `afk` (unrecognized → fail closed as hitl), means HITL. Missing `MODE:` means `afk`.

   The doc-side check is authoritative: labels are never re-synced after filing, so a title/label saying "afk" does not override a doc saying `MODE: hitl`.

   If any signal fires, ask via AskUserQuestion whether to proceed right now with a human in the loop. An explicit "no" → refuse, no state change, no claim. No answer possible — headless, `/loop`, cron, or any invocation with no one to answer — → refuse loudly, same shape as the `Backlog`-state refusal above: do not claim, do not transition state, report why.

   This gate re-fires on `--resume`. Unlike the state gate, which `--resume` deliberately bypasses, a `MODE: hitl` marker added mid-flight must still stop a resumed run — re-run this check before resuming, not just on first claim.

7. **SOUL.md gate.** Resolve SOUL.md in this order (same resolution as `/promote-issue`):
   - `packages/<pkg>/SOUL.md` when TOUCHES paths are under `packages/<pkg>/`.
   - `documentation/<project>/SOUL.md` when the source plan lives under `documentation/<project>/`.
   - Repo root `SOUL.md` as fallback.
   
   Extract the "Forbidden patterns" table and the "Tests for alignment" questions. If the Tier-2 TOUCHES or the recommended fix from Tier-1 matches a forbidden pattern, STOP before claiming — post a comment on the issue explaining the conflict and suggest a plan-doc revision. Do not transition state.

8. **Scope sanity.** Parse `ALLOWED` paths from the Tier-2 `<h3>Scope</h3>` block. Every allowed path must exist on disk (or be a directory that could plausibly hold new files). A dangling path means the Tier-2 drifted since promotion — note in session log, don't auto-abort unless EVERY allowed path is dangling.

   **Plan-graph sanity.** If the plan dir was validated at filing time (`/plan-to-plane` runs `omp-squad plan-validate`), trust it.

9. **Git state.** Working tree SHOULD be clean; if not, note the dirty paths. Never `git stash` on the user's behalf without permission. If dirty paths overlap with ALLOWED paths, refuse and ask the user to commit or stash first.

## Phase 1 — CLAIM

One MCP write, one MCP comment, no source edits. Reversible.

1. `mcp__plane__update_work_item(work_item_id, state=<In Progress uuid>, assignees=[<self_uuid>])`.
2. `mcp__plane__create_work_item_comment` with a body shaped like:
   ```
   Claimed by @<self> on <ISO timestamp> via /claim-and-implement.
   Intent: <one-sentence restatement of the Tier-1 "Why-now recommendation" section>.
   Branch: <current git branch>.
   Baseline acceptance test will be run next; implementation follows only if it fails.
   ```
3. Echo the issue URL to the user.

If `--resume` is passed: skip step 1 (already `In Progress`), still post a resume comment noting "resumed on <timestamp>; prior claim comment at <url>."

## Phase 2 — PARSE

Extract the six-field Tier-2 schema from `description_html`. Tolerate both the canonical HTML layout from `/promote-issue` and minor hand-edits (stray `<br>` tags, bullet-style variance). Do NOT tolerate missing fields — refuse and escalate.

Fields to extract:

- **Touches** — list of `path:lines — note` items. For each, verify the path exists; if drift has shifted line numbers by ≤20 lines, auto-correct and note the drift in session log; if >20 lines or the path is gone, flag as design drift and stop.
- **Acceptance test** — the exact command string. Capture verbatim.
- **Verification gate** — the exact command string. Capture verbatim.
- **Scope** — ALLOWED set + DENIED set. Normalise to absolute paths.
- **Expected vs. actual** — two short paragraphs; keep for the CLOSE comment evidence.
- **Reference implementation** — optional; if present, resolve any file/commit reference and read it during IMPLEMENT.
- **Hotspot reminders** — load-bearing. If a reminder says `state.rs` / `flows.yaml` / DFD, the privacy-model gate is non-negotiable during VERIFY.

Then read the **source plan doc** cited in the Tier-2 header `<em>Source plan: <code>...</code></em>`. Specifically scan for:
- `## Risks` or `## Out of scope` sections — caveats Tier-2 may have compressed away.
- `## Rollout` / `## Feature flag` — whether the fix ships behind a flag.
- `## Test plan` beyond the one-line acceptance test — deeper coverage the agent should add.

## Phase 3 — BASELINE

Run the Acceptance test exactly as captured. Capture stdout + stderr + exit code.

Three possible shapes:

1. **Fails with the expected signature** (most common). Proceed to IMPLEMENT. Preserve the output verbatim — it becomes evidence in the CLOSE comment.
2. **Passes already** (closure-detection path). The work may have shipped under a different ticket. Investigate:
   - Grep `~/.claude/projects/.../memory/*.md` for closure notes matching the concern id or title keywords (same pattern as `/promote-issue` Phase 1a).
   - `git log --all --oneline` for commits mentioning the concern id.
   - If a closure signal is found, skip to CLOSE with state → `Done` and a comment citing the closure evidence.
   - If no closure signal but the test passes anyway, STOP and surface to user: "Acceptance test already passing without evidence of prior closure. Design drift or stale test shape — investigate before implementing."
3. **Fails with an unexpected signature** (e.g., compile error, missing file, import cycle). The baseline world is broken in a way the promotion didn't capture. STOP. This is NOT the class of bug the ticket is scoped to fix. Surface to the user with the full failure output.

## Phase 4 — IMPLEMENT

The only phase that is irreducibly agentic. Everything else is a gate.

**Ordering.** Follow TOUCHES in dependency order. Heuristic:
1. Define types before consumers.
2. Define on-chain state/account shape before processors that read it.
3. Define server response shape before client parser.
4. Define schema/migration before any reader.
5. Test files come LAST only if the test is authored fresh; if the test is pre-existing (baseline), leave it untouched.

**Scope discipline.** Every `Edit` / `Write` call must target a path under ALLOWED. If mid-implementation you discover a necessary change outside scope:

1. STOP implementing.
2. `mcp__plane__create_work_item(project_id, name="<related concern title>", description_html=<why this surfaced + what needs to change>, state=<Backlog uuid>, priority="medium", labels=[<scope-creep label>])`.
3. Link the new issue to the current issue via `mcp__plane__create_work_item_relation` (relation_type=`blocks` if the current work truly cannot complete, else `relates_to`).
4. Post a comment on the current issue explaining the discovery and the filed follow-up.
5. If the discovery BLOCKS the current work: transition current issue back to `Todo`, remove self-assignment, report to user. If it doesn't block: continue, noting the follow-up in the session log.

**Privacy-model hotspots.** Read the "MANDATORY: Privacy-model discipline" section of the resolved package CLAUDE.md — it is the source of truth for which paths trigger the full privacy-model chain (dagon's enumeration is mirrored in `references/hotspots-dagon.md`).

**Existing-pattern preservation.** Before writing a new function/handler, grep for the closest existing sibling. New code should look like it belongs. If the plan doc cites a `Reference implementation`, read it before writing.

**No TODO markers.** Do not leave `TODO`, `FIXME`, `HACK`, or `XXX` in implementation output. If something is genuinely out of scope, file a concern per the scope-creep path above. A `TODO` in committed code is scope debt that won't be tracked.

## Phase 5 — VERIFY

Run the Verification gate exactly as captured. Capture full output.

**Two-strike rule.** If the gate fails:
- **First failure.** Read the output carefully. Make targeted fixes within ALLOWED scope. Re-run.
- **Second failure on the same signature.** STOP. Do not attempt a third time. The failure is architectural, not an execution error — the approach is wrong, the design is stale, or a hidden dependency is missing. Summarise what was tried + the common failure shape + hypotheses for the user. Hand back.

If the gate fails on a DIFFERENT signature the second time, treat that as the first strike of a new class — you've made progress — and allow one more attempt. But no more than four total attempts per invocation across all signatures; beyond that, the invocation is no longer productive.

**Hotspot gate.** If any privacy-model hotspot was touched, the full chain must pass:
```
pnpm check:privacy-model && pnpm test:privacy-model
```
A skipped privacy-model step counts as a verification failure, regardless of what the original gate said.

**Clean vs. noisy warnings.** New warnings introduced by this work must be resolved. Pre-existing warnings can be noted but do not block.

## Phase 6 — ACCEPT

Re-run the Acceptance test. Capture output.

It MUST pass. If it doesn't:
- First failure post-implement: read output, make targeted fixes, re-run VERIFY, re-run ACCEPT.
- Second failure: STOP — see Phase 5 two-strike. The implementation has a gap the baseline didn't predict.

If the test's assertion shape changed mid-implementation (i.e., you found yourself editing the acceptance test itself to make it pass): STOP. That's design drift, not a fix. The acceptance test is the contract — reshaping it to pass is cheating. Hand back to user.

Save the passing output — it's the closing evidence.

## Phase 7 — COMMIT

Commit in logical groups, message style per repo config (CLAUDE.md or AGENTS.md). Two non-default rules:

1. **Do NOT add "Generated with Claude" / "Co-Authored-By: Claude"** — repo config (CLAUDE.md or AGENTS.md) explicitly forbids this for non-Dagon commits; submodule defaults from `~/.claude/CLAUDE.md` for commit formatting apply.
2. **Do not push.** Auto-memory `feedback_superproject_push.md` says the user pushes the superproject manually at end of session. Submodule pushes (Dagon, IKA, Switchboard) are fine per that memory — but default to not pushing unless the user explicitly instructed "push this."

Capture each commit SHA; these become evidence in the CLOSE comment.

## Phase 8 — CLOSE

Four bookkeeping steps, all non-optional. Skipping any of them leaves drift behind.

### 8a — Plane state + close comment

0. **Push-reachability gate** (added 2026-07-03 by the wave1-trust plan — Done must carry post-merge proof):
   - `git fetch origin <default-branch>` in the target repo.
   - For every Phase-7 commit SHA: `git merge-base --is-ancestor <sha> origin/<default-branch>`.
   - **All reachable** → proceed to Done below as normal.
   - **Any unreachable** → do NOT transition to Done. Leave the issue at In Progress, post the close comment from step 2 retitled "Implementation complete — pending land", note that Done will follow once the commits are pushed/merged, and stop. Do not push anything yourself (the no-push rule above still applies) — re-run 8a after the user lands the work.
1. `mcp__plane__update_work_item(work_item_id, state=<Done uuid>)`.
2. `mcp__plane__create_work_item_comment` with a body shaped like:
   ```html
   Closed by /claim-and-implement on <ISO timestamp>.
   
   <h4>Commits</h4>
   <ul>
     <li><code>&lt;sha&gt;</code> — &lt;subject&gt;</li>
     ...
   </ul>
   
   <h4>Acceptance test (post-fix, passing)</h4>
   <pre>&lt;captured output&gt;</pre>
   
   <h4>Verification gate (passing)</h4>
   <pre>&lt;captured output&gt;</pre>
   
   <h4>Notes</h4>
   <ul>
     <li>&lt;drift corrections, scope-creep follow-ups filed, hotspot touches&gt;</li>
   </ul>
   ```

### 8b — Plan doc STATUS

Open the source plan doc (from the Tier-2 header). Find the `STATUS: open` line in the concern file. Rewrite to `STATUS: done`. Append a `## Resolution` section at the bottom of the file:
```markdown
## Resolution

Closed <YYYY-MM-DD> via DAGON-NN (<Plane URL>). Commits: <sha list>.
<One-sentence summary of the fix.>
```

If the concern file has a `PLANE: DAGON-NN — <url>` line from `/plan-to-plane`, leave it untouched — the pointer is still valid; the STATUS change conveys closure.

### 8c — 00-overview.md annotation

If the plan directory has a `00-overview.md` with a `## Plane tracking` table or issue list, annotate the row for this issue:
```markdown
- [NN-concern](<url>) — DAGON-NN ✅ done (commit <short-sha>)
```

If the overview doesn't have a tracking section, skip — don't invent one.

If `00-overview.md` has a `## Decisions so far` section, append or update **this concern's own row only** — never touch another concern's row, and a later contradiction gets a new superseding row, not an edit to history:
```markdown
- [<concern title>](NN-file.md) — <one-line gist>
```
The row is keyed by the `NN-file.md` link, so re-running this step is idempotent.

### 8d — Memory (conditional)

Add an auto-memory entry ONLY IF the implementation surfaced:
- A non-obvious pattern worth carrying forward (e.g., "Anchor 0.32 requires `solana_sdk_ids::ed25519_program` not `solana_program::ed25519_program`").
- A gotcha that cost >30 minutes to debug.
- A confirmed assumption previously marked uncertain (e.g., "Plane MCP `create_work_item_relation` does accept `blocks` as relation_type").
- A drift between plan-doc line numbers and actual source (systemic — worth warning future promotions).

Do NOT add memory for:
- Routine completions where everything went to plan.
- Obvious patterns already documented in CLAUDE.md / existing memory.
- One-off debugging that won't recur.

Write to the project's auto-memory directory as a new `feedback_<topic>.md` or `project_<topic>.md` file and update `MEMORY.md` index to link it.

## Failure modes (explicit)

| Mode | Detection | Response |
|------|-----------|----------|
| **Scope creep** | An Edit target is outside ALLOWED | File new concern via MCP, link as blocks/relates_to, either continue without the scoped-out change or hand back |
| **2-strike gate failure** | Same failure signature twice in VERIFY | see Phase 5 two-strike |
| **SOUL violation** | TOUCHES matches forbidden pattern | Refuse at pre-flight, before CLAIM. Comment on Plane explaining. No state change. |
| **Acceptance-test reshape** | You caught yourself editing the test to make it pass | STOP. That's cheating. Hand back; the plan's acceptance contract is wrong and needs redesign. |
| **Closure-discovery** | Baseline already passes AND memory/git log shows prior closure | Skip to CLOSE with `Done` + citation. No implementation. |
| **Stale TOUCHES line numbers** | Drift >20 lines or path gone | STOP at PARSE. Surface as design drift; promotion needs redo. |
| **Dirty working tree overlaps ALLOWED** | `git status` shows uncommitted overlap | Refuse at pre-flight. Never `stash` on behalf of user. |
| **Mid-implement user interrupt** | User injects a course-correction | Accept course-correction as normal input (auto-mode semantics). Re-evaluate scope before resuming. |

## Flags

`--dry-run` (no Plane writes, no source edits, no commits — print the full plan), `--resume` (re-fires the HITL gate, re-parses Tier-2, resumes from the earliest incomplete TOUCHES entry without re-claiming), `--scope-audit-only` (pre-flight + baseline + scope-drift report only). Full behavior: `references/flags.md`.

## When NOT to use this skill

- **On compliance / process / legal issues with no code deliverable** (e.g., P0-4 counsel questions, H5 external-audit scheduling). There's nothing to BASELINE or VERIFY; the ticket needs a human owner and a non-code resolution path.
- **On research-track issues** (P2-4 zkFHE investigation, P2-5 formal methods exploration). No implementable acceptance test exists; the output is a memo, not a passing test. Handle conversationally.
- **On issues blocked on external dependencies** (Encrypt queue items, upstream library pins). The ticket should be `Backlog` with an `external-dep` label; if it's `Todo` by mistake, re-label and return to Backlog.
- **On batch closures across many issues.** This skill is strictly one issue at a time. A batch sweeper is a separate skill (`/sweep-done` — not yet written).
- **During an active incident.** The skill's gates will slow you down; during an incident the human should run the commands directly.

## Reference

- `~/.claude/skills/plan/SKILL.md` — upstream source of the concern file format and STATUS conventions this skill closes.
- `~/.claude/skills/plan-to-plane/SKILL.md` — creates the Plane issues this skill consumes.
- `~/.claude/skills/promote-issue/SKILL.md` — enriches the Plane issues with the Tier-2 schema this skill parses. Most relevant prior art for pre-flight / SOUL / hotspot conventions.
- `~/.claude/skills/wip/` + `/sync-plans` — complementary WIP-visibility skills; this skill's Phase 8b is what keeps their scanner honest.
- `reference_plane_mcp.md` in auto-memory — Plane MCP invariant (MCP, not REST).
- `feedback_superproject_push.md` in auto-memory — why Phase 7 does not push.
- `packages/dagon/CLAUDE.md` — authoritative verification gate for Dagon; privacy-model hotspots enumerated.
- SOUL.md at `packages/<pkg>/SOUL.md` or `documentation/<project>/SOUL.md` — loaded in pre-flight; forbidden-pattern table is load-bearing.

## Downstream composition

- `/sweep-done` (not yet written) — batch variant for sweeping many Done-eligible issues at once.
- `/retro <DAGON-NN>` (not yet written) — reflective variant for generating a post-implementation retro from the session log; feeds learnings back into CLAUDE.md / MEMORY.md.

Until those exist, cadence is:
1. `/plan` produces `plans/<goal>/`.
2. `/plan-to-plane plans/<goal>/` files Backlog issues.
3. `/promote-issue <DAGON-NN>` upgrades one to Todo.
4. `/claim-and-implement <DAGON-NN>` executes it end-to-end.
5. User reviews + pushes.
