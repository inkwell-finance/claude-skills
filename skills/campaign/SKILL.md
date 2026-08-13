---
name: campaign
description: Run a goal-locked build campaign end-to-end — optional /research pre-map, wayfinder-style decision graph on an issue tracker, autonomous drive through decisions into enriched build tickets, parallel worktree builders, and blind cross-lineage gauntlet reviews with adjudicated receipts. Use when the user wants a large effort taken from loose idea to shipped, fully verified product ("campaign this", "graph/gauntlet/goal loop", "wayfinder + gauntlet", "take X all the way"). Not for single tickets (/claim-and-implement), quick fixes (/remediate), or plan-only decomposition (/plan).
---

# Campaign

Loose idea → cleared decision graph → gauntlet-verified product, autonomously. This composes four things that work badly apart and well together: **research** (pre-map the landscape), **wayfinder** (the graph: decisions as tickets, blocking edges as the frontier), **the goal loop** (a stop condition that keeps the orchestrator driving), and **the blind gauntlet** (builder vs fresh-context cross-lineage critics, looped until the artifact beats a real-world reference).

```
GOAL → [RESEARCH] → CHART (graph) → DRIVE (goal loop) ⇄ BUILD (parallel lanes) ⇄ GAUNTLET (blind critics) → DESTINATION
```

The orchestrator never implements and never reviews — it charts, routes, adjudicates, and merges. Every other role is a subagent with exactly one job.

## Phase 0: GOAL

Two questions are genuinely the user's; ask them once, together, and nothing else:
1. **Destination** — what does "done" look like (a spec? a decision? a shipped phase?). Recommend the option matching the project's own sequencing doc if one exists.
2. **Tracker** — where the map lives. Prefer a tracker with **native blocking** (GitHub issues + sub-issues + dependencies API; Plane relations). Local markdown is the no-tracker fallback.

If the user sets a goal/stop condition ("reach X, fully featured"), record it in the map's Notes as an **execution override**: the map carries execution, HITL pacing is overridden, and grilling-type decisions resolve autonomously **on recorded authority** — the project's spec docs, research briefs, and prior decisions — never on invented preference. Every autonomous resolution says so and is reopenable.

## Phase 1: RESEARCH (optional but cheap to skip wrongly)

If the effort has prior art (an existing corpus, a competitor, a design lineage), run `/research` first. Its BRIEF.md becomes a **settled input** listed in the map's Notes — tickets reference it instead of re-litigating it. Skip only when the landscape is genuinely bare.

## Phase 2: CHART

One session. Repo + tracker infrastructure first (git init / labels: `wayfinder:map`, `wayfinder:research|prototype|grilling|task`), then:

1. **Map issue** (`wayfinder:map`): Destination · Notes (spec docs, settled inputs, methodology, model routing, skill adaptations) · Decisions so far (empty index) · Not yet specified (the fog) · Out of scope.
2. **Decision tickets** as child issues — a ticket is a question you can state precisely NOW (blocked is fine; vague goes to fog). Body = `## Question` plus context links. Types: research (AFK), prototype, grilling, task.
3. **Wire blocking second** (issues need ids): sub-issues under the map + native blocked-by edges. The frontier = open ∧ unblocked ∧ unclaimed, visible in the tracker's own UI.
4. **Fire research subagents immediately** — they are the one type charting resolves. Parallel, findings on throwaway `research/<name>` branches, resolution comment + close, orchestrator indexes the gist into Decisions-so-far as each lands.

## Phase 3: DRIVE (the goal loop)

Repeat until the destination holds: take the frontier, resolve it, graduate the fog, dispatch builds. Rules proven in the field:

- **Decision tickets**: resolve with a `**Resolution**` comment stating the answer, the authority it rests on, and "reopen if wrong"; close; append one gist line to the map's Decisions-so-far. Detail lives in exactly one place — the ticket; the map only indexes.
- **Fog graduation**: when a resolution makes a build specifiable, create the build ticket **enriched at birth** — never sparse. Required sections: `## Question` (one line), `## Context` (links to governing resolutions), `## Touches` (paths), `## Acceptance test` (concrete, runnable), `## Verification gate` (the commands that must be green), `## Scope boundary` (what NOT to build; name the ticket that owns it), `## Gauntlet` (the real-world reference + which judges). A build ticket an agent can't pick up cold is a defect.
- **Tickets decay between writing and dispatch**: the orchestrator writes them from session memory, and lanes advance underneath. Every builder prompt says *verify the ticket's factual claims against the tree and report each contradiction rather than inheriting it*. Measured: one short ticket written from memory carried four wrong facts (branch count, heading count, a spec's own enumeration, two lanes a round stale) — all four caught by the builder in its first pass.
- **Tell agents waiting on long jobs to block, not report.** An agent that checks a running job, reports progress and stops turns the wait into a poll loop through the orchestrator — measured at three near-identical updates from one round, none carrying information. Say "block on the process and send one message when you have the answer", and enumerate in the dispatch exactly what that message must contain.
- **Give shared doctrine an append-only slot, and simulate the merge train early.** Measured: seven parallel lanes produced **zero source conflicts** and five conflicts on one prose file, because nearly every round's brief required a doctrine correction — a merge conflict specified in advance. Either give each lane a dated append-only section, or schedule doctrine edits as one pass after the train. And **simulate the sequential train in a throwaway branch long before you need it**: it costs one command, and a pairwise conflict matrix (which showed 9 of 10 pairs conflicting) is technically correct and practically misleading, because it never models the sequence anyone will actually perform.
- **Set `isolation: worktree` on the dispatch.** Telling an agent in prose to "work in your worktree" does not create one — measured: of two fix rounds dispatched with the instruction but without the parameter, one complied and the other ran `git checkout -b` in the orchestrator's own primary working directory, moving the session's checkout onto a build branch mid-run. Related habit that contained it: **every scripted edit asserts the text it expects before writing**, so the wrong-branch edit failed loudly instead of appending a file's history onto a branch that never carried it.
- **Parallel lanes**: anything whose blocking edges are clear AND whose files aren't being reshaped by an in-flight fix round can run concurrently — worktree isolation per builder, distinct branches, orchestrator owns merge order. Do not build atop files a fix round is rewriting; that's the one dependency the graph doesn't show.
- **A disagreement between lanes is a merge-tree property until proven otherwise**: when two parallel lanes measure the same property and get different answers, do not assume one measured badly. Ask which half of the mechanism each branch holds — the shipped behaviour is frequently visible from neither vantage point, and a branch-local measurement of a cross-branch property is not evidence about what ships. Keep the ticket that owns the number open until it is re-measured on the merged tree.
- **Never fabricate progress**: index only what a notification confirmed; a pending agent's result does not exist yet.
- **Reconcile the board against the *tracker* on a schedule, and weight the sweep by consequence.** Three lanes stalled in one campaign, each found by accident: two with a pushed branch and no gauntlet dispatched, one with a receipt never written. The mechanism is always the same — **attention follows notifications, and a lane that stopped producing them is indistinguishable from a finished one.** The lane most likely to go unnoticed is the one nobody is arguing about, which in one case was the auth boundary. Diff every lane's latest pushed branch against its latest receipt, don't trust the felt sense of having kept up.
- **Reconcile the board against the actually-running agents, periodically.** A dispatched agent is not a running agent. Measured twice in one campaign: two branches reported as live for fourteen hours were never gauntleted, and two critics vanished without reporting, leaving a pushed and receipted branch with no review at all. The drift is always in the direction that looks like progress. Also re-derive what a critic is pointed at from the tracker at dispatch time — one pair was aimed at a branch that did not yet exist, so even a verdict would have described superseded code.

### The destination gate (added after a campaign drifted for a day)

**Before dispatching any round, name the destination ticket it unblocks.** "None directly" is a legal answer and must be stated. Count consecutive dispatches that unblock nothing — that number drifting upward *is* the drift signal, and it is the only one the loop produces.

The exit rule below stops a *lane* escalating. It cannot see that the frontier moved, because it asks one question about one artifact. Measured: twelve rounds across five lanes, every one finding a real defect, while the destination's own two build tickets sat at zero comments and zero branches. **The gauntlet loop is a quality mechanism, not a scheduler — the map is the scheduler.** Keep an explicit critical path on the map and re-read it at every dispatch.

**Merge continuously.** Lanes that diverge for days compose in ways nothing local can see: two branches, each internally consistent and each passing a terminal blind review, produced a dead product path with **zero merge conflicts** because their rules lived in different files and different languages. It surfaced as one red integration test on a tree where typecheck, lint and 2909 unit tests were green. Rebase lanes onto a shared integration branch daily and run the **integration** suite on the merged tree — a green typecheck proves nothing about a producer and its checker disagreeing.

## Phase 4: BUILD

**Resource discipline — measured the hard way.** Nine hours of unbounded dispatch on a 4-core box reached load average 21.9 sustained (5.5x oversubscribed), 25 of 31 GB used, 48 Chrome and 14 vitest processes, 9 database containers — and one dev server holding **16.5 GB and 91% of a core for 2h33m**, belonging to a critic that had finished hours earlier. Three rules:
- **Check load before every dispatch and cap concurrent heavy agents at `cores/2`** (~2-3 on 4 cores) — by cores, not by lanes. Not advice to the builder — a check the orchestrator performs and acts on: **only the orchestrator knows what else is running, so only the orchestrator can enforce it.** Read load average before dispatching; if it exceeds cores, wait rather than queue (a queued lane costs nothing; an oversubscribed box slows every lane at once and hides which one is stuck); treat a starved run as an orchestration defect and say so in the receipt rather than letting the round attribute it to the artifact. Browser suites emit `Protocol error (Runtime.evaluate)` under contention, which reads as a product defect and costs a re-run to disprove.
- **Every completion notification is a reap point**, not only a cue to dispatch the next round — kill processes rooted in the agent's temp dir, remove containers it created, delete its clone.
- **Put teardown in the dispatch**: "tear down anything you start — dev servers, containers, `/tmp` clones — and say in your report what you tore down." One critic did this unprompted at zero cost; the rest left infrastructure behind and none of them were wrong to, because nobody had asked.
- **And measure what a round costs.** Subagent token counts arrive with every completion — tally them per lane. A campaign that cannot say what a lane cost cannot notice a lane costing more than the destination is worth.

Model routing (shape, not smartness ladder — per ~/.claude/CLAUDE.md):
- **Iterative in-repo work** (must run suites, react to failures): opus-5 native subagent, `isolation: worktree`.
- **Self-contained specs** (mechanical, isolated diffs): codex `gpt-5.6-terra`, high effort, via a thin sonnet relay wrapper running `codex exec`.
- **AFK research**: sonnet scouts (web + write brief + branch + resolve ticket).
- **Taste-critical artifacts** (UI, prototypes): opus-5 minimum.

Builder contract (put it in every prompt): work from the correct base branch (often another unmerged build branch, not main — say which); verify with the ticket's gate before pushing; push the branch; post a comment with what was built + verification output; **leave the issue OPEN** — only the orchestrator closes, and only after the gauntlet.

## Phase 5: GAUNTLET

Every build ticket passes a blind gauntlet before it closes. **Full doctrine + incident receipts live in [references/gauntlet-doctrine.md](references/gauntlet-doctrine.md) — read it before running any gauntlet round.** The load-bearing rules:

- **Blind means blind**: critics get fresh context, never the builder's notes/comments/commit messages, never each other's findings, and never write to the tracker.
- **Cross-lineage by risk**: default = one foreign-lineage critic (codex) or one fresh Claude. Anything touching **trust, security, concurrency, auth, or a git-write path** runs BOTH foreign lineages (codex gpt-5.6-terra high + grok-4.5) — measured to catch disjoint defect sets. Rendered/visual artifacts add a Claude critic that actually drives the page (agent-browser, screenshots, both themes).
- **One gauntlet receipt per round**, posted on the ticket: each critic's verdict, what survived adjudication, the routing table (fix round vs owning tickets vs noted-not-blocking), and what round 2 requires.
- **Adjudicate before acting**: a finding is a hypothesis.
- The one question that generalises every defect this process has caught: **_if I flip the input, does the output move?_** Structure proves where a value came from; only mutation proves it was *used*. Put it in every critic prompt and every builder's verification gate.

## Phase 6: RETRO (standing, not terminal)

Retrospection is structural from day one, not a post-mortem. Create `RETRO.md` at the repo root during CHART with three standing rules: (1) **every closed build ticket appends an entry** — rounds taken, what each gauntlet round caught, findings refuted with evidence, one process lesson; no entry, no close. (2) **Everything expirable names its expiry condition** — fog entries state what they hang on (graduation is mandatory when it clears), decisions carry "reopen if wrong", briefs carry provenance headers. A weekly **automated staleness sweep** (cron) checks idle tickets, unmerged branches, fog-with-cleared-blockers, missing retro entries, and drifted metrics — findings comment on the map; a missing sweep comment >10 days is itself the top finding. (3) **Stay youthful** — phase-boundary retros must prune at least one process rule (kill it or re-justify in writing), fund one cheap divergent pass at something that already "works", track reopens as a vitality metric (zero-over-a-long-stretch is a warning), and rotate one critic lens per phase so critics don't groove. Transferable lessons promote upward: repo lessons stay in RETRO.md, cross-project lessons go to auto-memory, doctrine changes edit this skill.

## Anti-patterns (each cost something once)

- Sparse build tickets whose real spec lives in the orchestrator's session ("nobody should re-derive context" — enrich at birth).
- Letting critics or builders close tickets that need adjudication (research tickets are the one exception — their resolution IS the deliverable).
- Piping critic output through `tail`/`head` and losing the verdict.
- Treating "critic found missing X" as a defect when X is a scheduled ticket — route it, don't panic-fix it.
- Building #N+1 on files a fix round is reshaping because the graph said it was unblocked.
- A goal loop that resolves HITL decisions on invented preference instead of recorded authority — autonomous ≠ unaccountable; every resolution names its basis and stays reopenable.
