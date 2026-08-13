---
name: promote-issue
description: Upgrade a Plane issue from Backlog to Todo by enriching its body with Tier-1 reviewer context and Tier-2 agent implementation schema. Use before handing an issue to an implementation agent or a human who shouldn't re-derive the context. One issue at a time.
argument-hint: "<IDENT-NN> [--force] [--dry-run] [--plan-doc <path>]"
---

# promote-issue

The bridge from "this exists as a tracked concern" to "an agent or a fresh-eyes human can implement this without asking questions." Backlog issues carry triage context; Todo issues carry both **reviewer-facing research context** and **agent-facing implementation context**. This skill makes the transition mechanical and gated.

```
VERIFY → READ SOURCES → DERIVE SCHEMA (T1 + T2) → WRITE BACK → TRANSITION STATE
```

## Why this exists

A fully promoted issue serves two audiences. Conflating them is how issues end up either too thin for an agent or too decontextualised for a reviewer.

### Tier-1 — origin & research context (reviewer-facing)

Preserves *why this issue exists at all* so a reviewer (or future-self) can judge scope, options, and timing without re-reading the source plan. Six sub-fields, derived from the plan doc's narrative sections:

1. **Discovery** — date + mechanism (audit, review, incident, external report).
2. **Severity rationale** — why this matters in plain language; the adversary/impact framing.
3. **Why the fix is non-trivial** — the constraint(s) that made options *exist* (CPA-secure ciphertexts, hotspot migration, external gate, etc.). If a plan has no such section, the plan is probably too thin to promote.
4. **Options considered** — every `### Option X` from the plan doc, each with its one-line cost estimate + tradeoff.
5. **Recommendation rationale** — not just the chosen option, but *why now / why this one*. The "no wasted work if Option B supersedes" shape of argument.
6. **Interim mitigation** — what's protecting us today while the fix is pending (doc blocks, session-cookie paths, demo-only surfaces). Failure to cite these is how a reviewer mistakes an "open" concern for a live exploit.

Tier-1 is pure narrative; it contains no instructions. Agents can safely ignore it. Humans need it.

### Tier-2 — implementation context (agent-facing)

SWE-bench ablation studies (Yang et al. 2025) and Devin / OpenHands production deployments converge on **six context fields** that correlate with agent success at ≥60% merge rate:

1. **Path references** — absolute file paths + relevant line ranges (not "the auth module").
2. **Acceptance test** — the exact command that, when it passes, means this is done.
3. **Verification gate** — the package's standard gate (`cargo check && cargo test`, `pnpm check:privacy-model`, etc.) from the relevant `CLAUDE.md`.
4. **Scope boundary** — directories the agent MAY and MAY NOT touch.
5. **Expected vs. actual** — current behaviour + target behaviour as short contrasting statements.
6. **Example diff / reference** *(optional, +15% success)* — a similar prior PR, a sibling concern's fix, or a patch sketch.

Verbose triage bodies *hurt* agent success (Princeton ablation: signal-to-noise matters more than volume). This skill enforces tight structure on both tiers — narrative in Tier-1, schema in Tier-2 — rather than letting them bleed into each other.

### Lesson from DAGON-9 backfill (2026-04-19)

The first version of this skill emitted only Tier-2. DAGON-9 was promoted with file paths, acceptance test, and verification gate — but nothing about *why* the concern was raised, what research framed the options, or which option the plan doc recommended and why. A reviewer asked "shouldn't there be a description of why this was raised?" and they were right. Plans had that context; promotion dropped it. Tier-1 is the fix. Every future promotion carries both.

## Pre-flight

1. **Plane resolution + MCP.** Per `reference_plane_mcp.md` (auto-memory, the owner of this contract): `.plane.json` → `PLANE_PROJECT_MAP`/`PLANE_PROJECT_ID` → `list_projects` → ask; MCP only, never REST curl fallback.

2. **Issue identifier parsed.** Accept any `<IDENT>-NN` (the prefix is the Plane project identifier). Map to project + sequence_id → retrieve work_item via `retrieve_work_item_by_identifier` (or `list_work_items(project_id, query="<IDENT>-NN")`).

3. **Idempotency check.** Read the current `description_html`. If it already contains BOTH `<h2>Tier-1 origin &amp; research context</h2>` AND `<h2>Tier-2 implementation context</h2>` blocks AND `--force` is not passed, skip and report "already fully promoted (T1+T2)." If only Tier-2 is present (legacy promotion from before this skill shipped Tier-1), treat the issue as eligible for Tier-1 backfill — derive and insert the Tier-1 block before the existing Tier-2 block without touching Tier-2, and report "Tier-1 backfilled onto pre-existing Tier-2." `--force` re-generates both.

4. **Plan-graph validity.** If the plan dir was validated at filing time (`/plan-to-plane` runs `omp-squad plan-validate`), trust it.

## Phase 1 — VERIFY

Read the current issue body. Extract:
- Title, priority, state, labels, parent, sequence_id.
- The `Source:` line — the plan doc this issue came from (e.g., `packages/dagon/plans/dagon-concern-30-account-id-binding.md`).
- Any other filesystem references in the body.

If no source plan doc can be found AND `--plan-doc <path>` was not passed, stop and report: "Issue has no linked plan doc; cannot derive tier-2 context. Pass `--plan-doc <path>` or add a Source: line to the issue body."

### 1a — Closure detection (ALWAYS run this check first)

Before deriving any tier-2 context, check auto-memory for a closure note matching this issue's topic. Grep `~/.claude/projects/.../memory/*.md` for:
- The concern id (e.g., `concern-30`).
- Keywords from the issue title (top 2-3 distinctive words).
- The source-plan basename without extension.

If a memory file begins with "CLOSED" or "shipped" referencing this concern, STOP the tier-2 derivation. Instead:
1. Transition the issue state to `Done`.
2. Post a `create_work_item_comment` citing the memory file + linking the referenced files/commits.
3. Report to the user: "Discovered during promotion — already shipped on YYYY-MM-DD. Closed the issue instead of promoting."

This is the single most important idempotency check — real-world finding: DAGON-31 was filed with a stale "gap exists" body when the gap had closed the day before. `/promote-issue` caught this and closed it instead of handing an agent phantom work.

The memory-first check is cheap (one grep) and prevents entire cycles of wasted agent effort on already-shipped features.

## Phase 2 — READ SOURCES

In parallel:

1. **Read the project SOUL.md** if one exists. Scan for SOUL.md in this order and use the first match:
   - `packages/<pkg>/SOUL.md` — for package-centric projects like Dagon (code + docs under one package root).
   - `documentation/<project>/SOUL.md` — for docs-centric projects like Leviathan, where code is scattered across multiple packages and the ethos lives next to the business thesis. Pattern: if the plan doc's `Source:` line points to `documentation/<name>/*.md`, check for `documentation/<name>/SOUL.md`.
   - Repo root `SOUL.md` — for company-level soul (cascades to all projects; not shipped yet).
   
   **This is load-bearing** — the six-field schema is about implementation correctness; SOUL encodes what makes a change *right for this project* beyond correctness. Specifically extract:
   - The "Forbidden patterns" table — if the tier-2 body would direct an agent into one of these patterns, REFUSE promotion and comment on the issue.
   - The "Tests for alignment" — carry the relevant question(s) into the tier-2 body's hotspot-reminder section. (E.g., if the change touches a data flow, include the "enumeration" alignment question as a reminder.)
   - Any forbidden-pattern match becomes an explicit comment on the Plane issue explaining why promotion was refused and what would need to change.
2. **Read the plan doc.** Full file.
3. **Read the package `CLAUDE.md`.** Determine which one by looking at file paths mentioned in the plan doc — if they're under `packages/dagon/`, read `packages/dagon/CLAUDE.md`. If under `packages/leviathan/` or similar, read that one. Fall back to repo-root `CLAUDE.md` if ambiguous. What we need from it: the package's verification gate command and the test-framework invariants.
4. **Read any referenced source files.** If the plan doc says "handler at `programs/dagon-pool/anchor/src/processor/read_balance.rs`", open it and resolve actual line numbers for the functions it references. Don't trust the plan doc's line numbers — they drift.
5. **Search for shared-file hotspots.** Read the "MANDATORY: Privacy-model discipline" section of the resolved package CLAUDE.md and check every file path in the plan doc against it. If any file in TOUCHES is a hotspot, the tier-2 body MUST include a mandatory privacy-model gate step.

## Phase 3 — DERIVE SCHEMA (Tier-1 + Tier-2)

Tier-1 is fail-soft: a missing sub-field is skipped (never fabricated) and the gap noted in the promotion report — the block ships partial. Tier-2 is fail-fast: refuse full promotion if a field can't be derived (Phase 5's partial path). Never collapse or omit a Tier-1 option; never accept "run the existing test suite" as an acceptance test; don't fabricate a reference diff.

| Field | Source section in plan doc | Max length | On missing |
|---|---|---|---|
| T1.1 Discovery | Opening metadata: `**Status:** … Identified YYYY-MM-DD during <mechanism>.`, `**Tracking:** …` | 1 paragraph, ≤3 sentences | skip + note gap |
| T1.2 Severity rationale | `**Severity:**` line + "Consequence" paragraph after `## Finding`; adversary / gain / loss framing | ≤3 sentences | write "Severity rationale not present in source plan" + flag |
| T1.3 Why the fix is non-trivial | `## Why the fix is non-trivial` / `## Constraints` / `## Background`; quote the core constraint verbatim | 1 paragraph | skip + note gap (plan likely too thin for Tier-1) |
| T1.4 Options considered | Every `### Option X — <title>`: title, summary, cost line, gating note — never collapse two, never omit a non-recommended one | ≤2-sentence summary per option | skip + note gap |
| T1.5 Why-now recommendation | `## Recommendation` — the reasoning: shape (flag-gated/phased), why now, wasted-work-if-superseded | 1 paragraph | skip + note gap |
| T1.6 Interim mitigation | `## Mitigation in the meantime` / `## Mitigation today`; "no mitigation today" is load-bearing — say it explicitly | bullets | skip + note gap |
| T1.7 Owner & timing | `## Owner` | 3 bullets (engineering / gate / ship target) | skip + note gap |
| T2.1 Path references | Plan-doc file paths with line ranges re-resolved against source (don't trust plan-doc line numbers) | — | fail fast |
| T2.2 Acceptance test | Prefer: existing failing-then-passing test → new named test + assertion → smoke script with expected output | exact command | fail fast |
| T2.3 Verification gate | The package `CLAUDE.md` verification section, copied verbatim | exact command | fail fast |
| T2.4 Scope boundary | TOUCHES paths → `ALLOWED:` dirs + `DENIED:` dirs | — | fail fast |
| T2.5 Expected vs. actual | "Finding"/"Current state" → Actual; "Recommendation"/"Fix"/"Evidence required" → Expected | 2 bullets each, ≤25 words per bullet | fail fast |
| T2.6 Example diff (optional, +15%) | Sibling closure trail / prior commit via git-log grep on the concern id / similar heavily-tested handler — 30-second search | — | skip, don't fabricate |

## Phase 4 — WRITE BACK

Build the new `description_html`. Preserve the existing triage body (above). Append the Tier-1 block first, then the Tier-2 block. Order matters: reviewers read top-down, and the narrative context is what scopes the schema.

Skeleton — these exact `<h2>`/`<h3>` anchor headings are what `/claim-and-implement` parses; fully-worked dagon example in `references/example-promotion-dagon.md`:

```html
<hr />
<h2>Tier-1 origin &amp; research context</h2>
<p><em>Emitted by /promote-issue on YYYY-MM-DD. Source plan: <code>path/to/plan.md</code>. Reviewer-facing narrative; agents can skip to Tier-2 below.</em></p>
<h3>Discovery</h3> <h3>Severity rationale</h3> <h3>Why the fix is non-trivial</h3>
<h3>Options considered</h3> <h3>Why-now recommendation</h3> <h3>Interim mitigation</h3>
<h3>Owner &amp; timing</h3>

<hr />
<h2>Tier-2 implementation context</h2>
<p><em>Promoted by /promote-issue on YYYY-MM-DD. Source plan: <code>path/to/plan.md</code></em></p>
<h3>Touches (files + lines)</h3> <h3>Acceptance test</h3> <h3>Verification gate</h3>
<h3>Scope</h3> <h3>Expected vs. actual</h3> <h3>Reference implementation</h3>
<h3>Hotspot / gate reminders</h3>
```

Write via `mcp__plane__update_work_item(work_item_id, description_html=<new body>)`.

## Phase 5 — TRANSITION STATE

If the issue is currently in `Backlog` AND all six fields were derived successfully (not placeholders), transition to `Todo`:
- `state = <Todo state uuid from list_states()>`

If any field was weak (e.g., no plan doc could be found but user passed `--plan-doc` anyway, or acceptance test couldn't be derived and falls back to smoke script), KEEP state as Backlog and write the partial context into the body anyway — it's useful pre-design material — but append a top-level `<h2>Tier-2 implementation context — BLOCKED ON DESIGN DECISION</h2>` (or similar specific blocker) instead of the plain tier-2 header. Include a dedicated section:

```html
<h3>Why /promote-issue refuses full Todo transition</h3>
<ul>
  <li><strong>Acceptance test:</strong> can't write a passing test without knowing X.</li>
  <li><strong>Scope boundary:</strong> conflict between Option A and Option B.</li>
  <li><strong>Verification gate:</strong> differs per option.</li>
</ul>
<p><strong>Recommended next action:</strong> [file ADR / ask counsel / run benchmark / etc]. Re-run <code>/promote-issue DAGON-NN</code> after the decision lands.</p>
```

This is a success case, not a failure — the skill surfacing hidden complexity that a dispatcher would otherwise hand to an agent blind. Real-world finding: DAGON-19 (Pyth threshold) was filed as "one-line change" per audit; promotion surfaced that the "constant" lives inside a byte-pinned FHE graph and either Design A (graph rebuild + hash re-pin) or Design B (state.rs hotspot + double-path-of-truth) is required. Neither is a one-liner. The skill refusing full promotion prevented an agent from silently picking one.

Then report to the user which fields came back strong vs. weak, and whether the issue was promoted, partial-promoted (still Backlog), or closed (already shipped).

## --dry-run

Skip `update_work_item` and `add_work_item_comment`. Print the new body + state transition that WOULD happen.

## --force

Re-generate even if Tier-1 and/or Tier-2 blocks already exist. Replaces both by matching on the `<h2>Tier-1 origin &amp; research context</h2>` and `<h2>Tier-2 implementation context</h2>` anchors. Preserves the prior triage body above.

## Reporting

After success:
1. Echo the Plane issue URL.
2. Echo the promotion summary, broken down by tier:
   - **Tier-1:** which sub-fields were derived from the plan doc (Discovery / Severity / Non-trivial / Options / Why-now / Interim / Owner) and which were skipped. A skipped sub-field is a signal the plan doc needs more thought — surface that in the report, don't hide it.
   - **Tier-2:** which of the six fields came from the plan doc, which from source-code grep, which are weak/smoke-only.
3. If a reference diff was found, cite it.
4. If any hotspot reminders applied, list them.
5. If any Tier-1 sub-field was skipped, explicitly invite a plan-doc improvement: "Consider expanding <plan-doc-path> with <missing section> before the next agent handoff."
6. Suggest the next step: "Ready for `/claim-and-implement` on Pyth threshold validation (DAGON-19) once that skill lands, or for a human engineer to pick up."

In report/summary prose shown to the user, wrap issue ids in their titles — e.g. `Pyth threshold validation (DAGON-19)`, never a bare `DAGON-NN` wall. This applies to every issue reference across all six reporting steps above, not just the closing suggestion. Machine-read surfaces are exempt: issue bodies, `Source:` lines, and `<pre><code>` blocks keep bare ids — those are load-bearing for idempotency markers and grep-based closure detection.

## When NOT to use this skill

- On compliance/legal/process issues that have no code deliverable (P0-4.x, H5.x). Those don't need a tier-2 body — they need a human owner.
- On issues blocked on external deps (Encrypt A4/A8/A14/A16, C5). Promoting them to Todo is premature; they're Backlog for a reason.
- On research-track items (P2-4 zkFHE, P2-5 formal methods). No implementable schema exists.

## Reference

- `~/.claude/skills/plan/SKILL.md` — where the concern file format originated.
- `~/.claude/skills/plan-to-plane/SKILL.md` — the companion skill that creates Plane issues from plan docs.
- `packages/dagon/CLAUDE.md` — authoritative verification gates for Dagon.
- `reference_plane_mcp.md` in auto-memory — Plane MCP setup notes.
- Research synthesis: SWE-agent 2 (Princeton), Devin (Cognition), OpenHands (All-Hands-AI), `imbue-ai/mngr` — the six-field schema is the intersection of these.
