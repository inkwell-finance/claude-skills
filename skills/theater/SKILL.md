---
name: theater
description: Orchestrate multiple /campaign runs — enumerate every wayfinder map across repos, report each campaign's frontier, gauntlet state, and distance to destination, surface the human-attention queue, and allocate lanes to the campaign that deserves them. Use for "theater", "what are my campaigns doing", "which campaign next", "allocate lanes", "campaign status across repos". Not for running a single campaign (/campaign), single tickets (/claim-and-implement), or plan-level WIP inside one repo (/wip).
---

# Theater

The layer above campaigns. A campaign has one destination and ends; a theater sequences many campaigns competing for the same scarce resources — model budget, rate-limit headroom, merge lanes, and (scarcest) the human's attention at decision points. Theater NEVER fights battles: it doesn't resolve tickets, build, or gauntlet. It observes, reports, sequences, and dispatches whole campaigns. Grand strategy — which campaign is worth running at all — stays with the human; theater's job is to make that call cheap to make.

```
/theater            → RECON report (default)
/theater <target>   → ZOOM one campaign (repo, map URL, or name)
/theater dispatch <target>   → start/resume a campaign session
/theater sequence   → propose campaign ordering + handoffs
/theater stand-down <target> → park a campaign, recorded on its map
```

## RECON

Discovery, in parallel:
1. **GitHub campaigns**: `gh repo list <user> --limit 400 --json name` (if the count equals the limit, raise it and re-run — a truncated roster silently hides campaigns) → for each repo (parallel, quiet): `gh issue list --label wayfinder:map --state all --json number,title,url,updatedAt`. A repo with no map has no campaign — skip silently.
2. **Plane campaigns**: if the plane MCP is connected, search work items labeled/titled `wayfinder:map` per project. Absence is normal.
3. **Pre-campaign efforts**: local `plans/` directories via the /wip scan are *staging areas*, not campaigns — list them under a separate "not yet charted" line only if the user asked for the full picture.

Per campaign found, from the map issue + child tickets (one `gh api` sweep per repo, not per ticket):
- **Destination** — first line of the map's Destination section, verbatim.
- **Decisions**: closed vs open decision tickets (indexed lines in Decisions-so-far vs open non-task children).
- **Frontier**: open ∧ unblocked ∧ unassigned children — the takeable edge.
- **In gauntlet**: open build tickets whose last comment is a gauntlet receipt or fix-round report.
- **Blocked on human**: tickets whose resolution says "reopen if wrong" and touches a stated preference, prototype tickets awaiting reaction, any ticket assigned to the human.
- **Staleness**: newest updatedAt across map + children — plus flags: frontier tickets idle >7d, unmerged branches >7d old, fog entries whose named blocker has closed, missing weekly sweep comment on the map (>10d = the campaign's own staleness automation is dead; report it first).
- **Live lanes**: if this session (or a session log) shows running agents for the repo, count them; otherwise report lanes as unknown, never as zero.

Report: one table (campaign · destination gist · decisions closed/open · frontier · in-gauntlet · blocked-on-human · last activity), then the **attention queue** — every blocked-on-human item across all campaigns, hardest first, each with its why-you line and link — then one recommendation: which campaign gets lanes now, and why (attention-starved beats agent-starved; a campaign waiting only on gauntlet verdicts needs zero new lanes).

## ZOOM

One campaign: the map's Decisions-so-far as a timeline, open tickets grouped frontier / blocked / in-gauntlet with blocking edges shown, fog and out-of-scope verbatim, plus lane advice: which frontier tickets are parallel-safe (blocking edges clear AND no shared files with an in-flight fix round — the one dependency the graph doesn't show).

## DISPATCH

Start or resume a campaign as its own session — theater hands off, it does not inline the work:
- New effort: instruct the user to run `/campaign <goal>` in the target repo, or launch a background job/session there yourself if the harness allows.
- Existing map: the dispatch prompt is small — repo, map URL, "continue the campaign: work the frontier per /campaign phase 3–5" — because the map itself is the campaign's memory. That property is load-bearing: any session can pick up any campaign cold.
- **One campaign per repo at a time.** Two campaigns writing one repo means two merge-lane owners; refuse and say so.

## SEQUENCE

Campaigns hand off through artifacts, not vibes: a research campaign's BRIEF.md becomes the next campaign's settled input; a build campaign's shipped Phase becomes the dogfood campaign's substrate. Propose an order using: hard artifact dependencies first, then attention economics (batch the campaigns that will need the human this week), then rate-limit reality (two campaigns' worth of parallel opus/codex lanes will hit limits — stagger them). Output is a proposal; the human picks.

## STAND-DOWN

Parking is a scoping act, recorded like everything else: comment on the map ("stood down <date>: <why> — resume by working the frontier"), note what was mid-flight (unmerged branches by name, unadjudicated receipts), close nothing. A parked campaign must be resumable cold from its map alone; if it isn't, fix the map before parking.

## Doctrine

- Theater is read-mostly: its only writes are dispatch prompts, stand-down comments, and sequencing proposals.
- Never report a campaign healthier than its tracker shows; never count a pending agent's work as done.
- The attention queue is the product. Agents idle cheaply; humans blocking expensively. Surface human-blocked items before agent-idle items every time.
- If recon finds a map this skill's conventions can't parse (foreign wayfinder dialect), report it as unparsed rather than guessing its state.
