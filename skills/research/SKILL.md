---
name: research
description: Research an external project, tool, library, paper, or concept — scout it, dissect the implementation into transferable patterns, and map them onto the current project. Chains into /plan when actionable. Use when the user says "research X", "look into X" (external targets only — never for investigating this repo's own code or bugs), "scout X" (gather-only pass, no analysis), "what can we learn from X", "should we adopt X", "compare X and Y", "evaluate this tool", or asks to assess a URL/repo/package. (broad-topic fact-finding falls back to WebSearch)
argument-hint: "<url | repo | package | topic> [more targets...]"
---

# Research

Research an external project, tool, library, or concept. Distill and abstract the useful insights. If there's actionable intel, chain into `/plan`.

Unlike `/plan` (build something new) or `/remediate` (fix what's broken), `/research` is about **intelligence gathering** — understanding what exists in the world and extracting what's relevant to our system.

```
TARGET → SCOUT (parallel) → DISSECT+ABSTRACT (team: comparator → strategist) → PERSIST → (chain to /plan if actionable)
```

---

### Phase 0: TARGET

Establish **which project the intel maps onto** and **which question the research answers** before gathering any of it. The strategist's whole job is mapping patterns to a concrete codebase — pointed at the wrong one, the output is fiction; pointed at the wrong question, it's an accurate answer nobody asked for.

- Default: the repo containing the current working directory.
- If the invocation names a project, or the cwd is ambiguous (home dir, scratch dir), ask.
- Note the project's name, its architecture in one or two sentences, and where its plans live (`plans/` by convention; in a monorepo this is often the package's own `plans/`, not the repo root — look for existing `research-*` dirs). All downstream prompts reference **the target project** by name — never a placeholder.
- **QUESTION**: state in one line what decision this research informs. If the invocation carries intent, use it. A bare URL defaults by target type: for a library/paper/tool the target project might use, the question is *how is it built and what patterns transfer*; for a **competitor or analog of the target project**, the question is *why does it win — adoption, daily usage, what its practice knows that ours doesn't* — construction detail is secondary, since the architecture of an analog usually resembles our own. Write the question into the brief's provenance header. (This gate exists because a bare-URL run on a direct competitor once produced a faithful architecture brief that missed the user's actual question — the daily-use lens — entirely.)

---

### Phase 1: SCOUT

Gather comprehensive information about the research target.

**Input**: A URL, repo name, tool name, concept, paper, or general topic.

**Actions by input type**:

| Input | Approach |
|-------|----------|
| GitHub repo | `gh repo view`, `gh api` for README, file tree, key source files, package.json |
| URL / docs site | `WebFetch` the page, follow links to full docs (`llms.txt`, `llms-full.txt`, API reference) |
| npm/pypi package | Fetch registry metadata + GitHub source |
| Paper / concept | WebSearch for primary sources, then WebFetch |
| Pre-extracted artifact (e.g. `/crypto-research` markdown + target context) | Read the provided path(s) first; treat any supplied target context as Phase 0 input. Re-fetch only if the artifact is incomplete. |
| Broad topic | Run a plain WebSearch sweep to identify the top 3-5 concrete implementations, then SCOUT each. |

**What to extract** — two axes, both mandatory for repos; the artifact axis alone is a half-brief:

*Artifact axis (how it's built):*
- What it is (one sentence)
- What problem it solves
- How it works (architecture, data flow)
- Key design decisions and why they were made
- Tech stack and dependencies
- API surface / interface
- What makes it different from alternatives
- Source anchors: for repos, the commit SHA or release tag inspected; for packages, the registry version; for papers, the canonical URL/DOI

*Practice axis (how it's used and why it wins):*
- Who builds it and whether they dogfood it — a daily-driven tool encodes usage lessons a spec-driven one can't
- Change history as a usage diary: what pain got fixed fast (= felt by maintainers), what lingers (= off the dogfood path), which subsystems get continuous fixes (= most used)
- The author's/community's own account of real workflows (launch posts, talks, issue threads) — sourced, never from training memory
- Defaults and small QoL details as frozen usage opinions (what does zero-config assume?)
- Adoption story: what convinced users to switch, what stops them

For a repo target, scout both axes in parallel (source read + history mining + narrative search — separate scouts when the Phase 0 question warrants depth). When the Phase 0 question is *why does it win*, the practice axis leads and the artifact axis supports.

**Evidence rules**:
- Prefer source over marketing — if the README claims X, open the code that would prove X.
- If a primary source is unreachable (paywall, private repo, blocked fetch, rate limit), say so explicitly in the brief and mark the affected sections LOW-CONFIDENCE. Never fill gaps from memory silently.
- Never install, build, or execute researched code during `/research` — reading is the whole job.

**For multiple targets** (e.g., `research <url> <url>` or broad topic with 3-5 implementations): launch parallel sonnet scout agents, one per target. Each produces its own research brief. All briefs feed into the DISSECT+ABSTRACT team together.

**Output**: A **research brief** per target — concise but complete. Facts, not opinions. No recommendations yet.

**Gate (conditional)**: Present the brief(s), then proceed directly to DISSECT+ABSTRACT. Stop and wait for confirmation only if: (a) the target's identity or scope is still ambiguous, (b) scouting hit contradictions or an unreachable primary source that materially weakens the brief, or (c) the route went through a broad-topic WebSearch sweep and choosing which targets to dissect involves judgment. The load-bearing user gates are Phase 0 (right project) and Phase 3 (chain to `/plan`) — not here.

---

### Phase 2: DISSECT + ABSTRACT

#### Team composition

| Round | Role | Model | Count | Input | Output |
|-------|------|-------|-------|-------|--------|
| 1 | **Comparator** | sonnet | 1 | All scout outputs | Concept extraction table: implementation vs transferable pattern, cross-references between sources |
| 2 | **Strategist** | fable (opus when fable is unavailable) | 1 | Comparator output + target-project context from Phase 0 | Ranked abstract patterns with concrete application points + build-vs-buy assessment |

**Why this team**: DISSECT (separating concepts from implementations) is structured analysis — sonnet excels. ABSTRACT (ranking by impact, mapping to the target project's architecture, judging build-vs-buy) is strategic judgment — it gets the strongest available model.

**Single target, modest brief**: skip the separate comparator round — the strategist produces the concept table itself as step one of its work. The comparator's value is cross-referencing between sources; with one source there is nothing to cross-reference. Spawn the comparator only for multiple targets, or when the combined scout output is too large to sit comfortably in one strategist prompt.

**Comparator output format:**
```
| Concept | How they implemented it | Transferable? | Why / why not |
|---------|----------------------|---------------|---------------|
```

**Transferable** means: this idea could improve the target project regardless of whether we adopt this specific tool.

**Comparator rules:**
- Focus on ideas, not features. "Wide events" is a concept. "evlog's Nuxt module" is an implementation detail.
- Identify the **non-obvious** insights. The obvious ones (e.g., "has good docs") aren't useful.
- Note design tensions — where did they make tradeoffs? What did they sacrifice?
- If multiple research targets have been scouted, cross-reference. What patterns recur?

**Strategist output format** — for each transferable concept:
```
**Concept**: [name]
**Pattern**: [what it is, generalized — no reference to the source tool]
**Mechanism**: [how it works in practice — concrete enough to implement]
**Value for <target project>**: [specific benefit, referencing the target project's architecture]
**Where it applies**: [which repos, modules, or workflows it touches]
**Build vs Buy**: [borrow the pattern | adopt the dependency — with rationale]
```

**Strategist rules:**
- The abstraction must stand on its own. If you removed all mention of the source tool, the concept should still be clear and actionable.
- Be specific about where in the target project it applies. "Could improve logging" is too vague. "The daemon's error handling in `src/shared/logging/` could emit structured error events with `why`/`fix` fields to `events.jsonl`" is the level of concreteness required — real paths from the actual target project, verified to exist.
- Rank concepts by impact: which ones close the biggest gaps or unlock the most value?
- **Rank against the target project's known bottleneck, and name it.** Pull the project's top standing problem from auto-memory, CURRENT-STATE docs, or prior research briefs (e.g. "nobody dogfoods it", "tests are flaky", "no adoption") and weigh every concept against *that*, not against abstract architectural elegance. A concept that attacks the named bottleneck outranks a cleverer one that doesn't. If no bottleneck is on record, say so — that absence is itself a finding for the brief.
- Default to building the pattern, not adopting the dependency, unless the dependency solves a genuinely hard problem (crypto, consensus, etc.)

**Output**: A ranked list of **abstract patterns** with concrete application points in the target project.

---

### Phase 3: PERSIST

**Before the gate, not after.** Write `<plans-root>/research-<slug>/BRIEF.md` unconditionally — scout briefs, the comparator table, and the strategist's ranked concepts. `<plans-root>` is the plans directory identified in Phase 0: repo-root `plans/`, or the package's own `plans/` in a monorepo — put the brief where that project's existing `research-*` dirs already live, never a second plans tree. Slug: lowercase, hyphenated, derived from the target name. If the session dies or the `/plan` chain stalls, the research must survive. A brief that only exists in conversation is a brief that gets re-done from scratch next month.

BRIEF.md opens with a provenance header: date, every source URL, and the commit SHA or release version scouted — a reader six months out must be able to judge staleness and re-verify claims.

If `research-<slug>/` already exists from a prior run, read the old BRIEF.md first, then append a dated section recording what changed since — never overwrite prior findings.

**Gate**: Present the ranked concepts to the user. Two possible outcomes:

1. **Actionable intel exists** — user confirms concepts worth implementing → chain into `/plan` with the abstracted concepts as the goal, per the Handoff section below. BRIEF.md stays on disk as the durable record either way.

2. **Intel only** — concepts are noted for future reference, no immediate action. BRIEF.md is already written; nothing more to do.

---

## Handoff to /plan

When chaining into `/plan`, pass forward:
- The ranked concept list from ABSTRACT (this is the goal)
- Any specific target-project files/modules identified as application points
- Build-vs-buy assessment: borrow the pattern or adopt the dependency? If recommending adoption, include license and maintenance signals (last release, activity) in the assessment.
- The path to BRIEF.md

`/plan` knows nothing about research briefs — say so explicitly in the invocation: instruct its EXPLORE phase to treat BRIEF.md's verified application points as a pre-mapped landscape to validate and extend, not rediscover from zero. `/plan` then owns execution from EXPLORE onward. `/research` is done.

**Rules for handoff**:
- Never recommend adopting a tool wholesale without justification. Default to borrowing the pattern, not the dependency.
- If the tool itself is genuinely the right choice (mature, maintained, solves a hard problem), say so — but compare build-vs-buy explicitly.
- If a `/plan` is already active and the concepts fit, propose modifications to the existing plan rather than starting a new one.

---

## Scope Interpretation

| Input | Behavior |
|-------|----------|
| `research <url>` | Full pipeline: TARGET → SCOUT → DISSECT+ABSTRACT → PERSIST → (handoff) |
| `research <url> <url>` | SCOUT both in parallel, cross-reference in DISSECT+ABSTRACT |
| `research <topic>` | WebSearch sweep (per Phase 1) to find concrete targets, then full pipeline |
| `scout <url>` | SCOUT only — just gather and present, no analysis |

## Anti-Patterns

- Presenting ranked concepts that were never written to BRIEF.md
