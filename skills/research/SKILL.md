# Research

Research an external project, tool, library, or concept. Distill and abstract the useful insights. If there's actionable intel, chain into `/plan`.

Unlike `/plan` (build something new) or `/remediate` (fix what's broken), `/research` is about **intelligence gathering** — understanding what exists in the world and extracting what's relevant to our system.

```
SCOUT (parallel, + alternatives scan) → DISSECT+VERIFY+ABSTRACT (team: comparator classifies & verifies → strategist) → (chain to /plan if actionable)
```

---

### Phase 1: SCOUT

Gather comprehensive information about the target.

**Input**: A URL, repo name, tool name, concept, paper, or general topic.

**Actions by input type**:

| Input | Approach |
|-------|----------|
| GitHub repo | `gh repo view`, `gh api` for README, file tree, key source files, package.json |
| URL / docs site | `WebFetch` the page, follow links to full docs (`llms.txt`, `llms-full.txt`, API reference) |
| npm/pypi package | Fetch registry metadata + GitHub source |
| Paper / concept | WebSearch for primary sources, then WebFetch |
| Broad topic | WebSearch to identify the top 3-5 concrete implementations, then SCOUT each |

**What to extract**:
- What it is (one sentence)
- What problem it solves
- How it works (architecture, data flow)
- Key design decisions and why they were made
- Tech stack and dependencies
- API surface / interface
- What makes it different from alternatives

**Tag every claim with its source.** For each non-obvious claim — especially performance ("10x faster"), scale, or capability assertions — record where it came from (file/URL) and whether it is **vendor-asserted** (the project's own docs/README/marketing) or **independently sourced** (third-party benchmark, neutral comparison, your own reading of the code). This provenance travels with the claim through every downstream phase. SCOUT does not verify yet — it just refuses to launder a marketing claim into a "fact."

**Alternatives scan (always, even for a single target).** Before finishing, spend one lightweight WebSearch naming 2-3 competing approaches in the same space, one line each: what they are and how they differ. For a single `research <url>`, the only alternatives signal otherwise comes from the target's own framing — which is biased toward adoption of the first thing you looked at. Naming the field independently both counters that bias and gives VERIFY a yardstick to check the target's "what makes us different" claims against.

**For multiple targets** (e.g., `research <url> <url>` or broad topic with 3-5 implementations): launch parallel sonnet scout agents, one per target. Each produces its own research brief. All briefs feed into the DISSECT+ABSTRACT team together.

**Output**: A **research brief** per target — concise but complete. Facts, not opinions. No recommendations yet.

**Gate**: Present the brief(s) to the user. Confirm understanding before moving to DISSECT+ABSTRACT.

---

### Phase 2: DISSECT + VERIFY + ABSTRACT

#### Team composition

| Round | Role | Model | Count | Input | Output |
|-------|------|-------|-------|-------|--------|
| 1 | **Comparator** | sonnet | 1 | All scout outputs | Concept extraction table + evidence classification + verification of load-bearing claims |
| 2 | **Strategist** | opus | 1 | Comparator output + behemoth codebase context | Ranked abstract patterns with concrete application points + build-vs-buy assessment + confidence |

**Why this team**: DISSECT (separating concepts from implementations) is structured analysis — sonnet excels. VERIFY (classifying each claim's evidence basis and checking the load-bearing ones) is folded into the comparator round — it's structured, not strategic, so it needs no separate gate or opus call. ABSTRACT (ranking by impact, mapping to behemoth architecture, judging build-vs-buy) is strategic judgment — opus excels. The strategist consumes the comparator's verified, provenance-tagged extraction rather than raw scout claims.

**Comparator output format:**
```
| Concept | How they implemented it | Transferable? | Why / why not | Source | Evidence basis |
|---------|------------------------|---------------|---------------|--------|----------------|
```

`Evidence basis` ∈ `vendor-asserted | third-party-benchmarked | verifiable-from-code | unverifiable`.

**Transferable** means: this idea could improve behemoth regardless of whether we adopt this specific tool.

**Comparator rules:**
- Focus on ideas, not features. "Wide events" is a concept. "evlog's Nuxt module" is an implementation detail.
- Identify the **non-obvious** insights. The obvious ones (e.g., "has good docs") aren't useful.
- Note design tensions — where did they make tradeoffs? What did they sacrifice?
- If multiple research targets have been scouted, cross-reference. What patterns recur?
- **Classify the evidence basis of every load-bearing claim** — fill the `Source` and `Evidence basis` columns. A claim is *load-bearing* if its being false would flip the build-vs-buy decision or kill the reason to adopt.
- **Verify the load-bearing ones; just classify the rest.** For each load-bearing claim still `vendor-asserted`, spend a real check — search for an independent benchmark, or read the source to confirm the mechanism exists — and update its evidence basis. Cheap or non-load-bearing claims get classified, not chased. This is the tiered gate: don't burn effort verifying trivia, but never let a marketing number become a premise unchecked.
- **Flag** anything that remains `vendor-asserted` or `unverifiable` so the strategist (and any downstream `/plan`) can see which premises are soft.

**Strategist output format** — for each transferable concept:
```
**Concept**: [name]
**Pattern**: [what it is, generalized — no reference to the source tool]
**Mechanism**: [how it works in practice — concrete enough to implement]
**Value for behemoth**: [specific benefit, referencing behemoth's architecture]
**Where it applies**: [which repos, modules, or workflows it touches]
**Build vs Buy**: [borrow the pattern | adopt the dependency — with rationale]
**Source**: [where each load-bearing claim came from + its evidence basis, carried from the comparator]
**Confidence**: [high = load-bearing claims independently confirmed | provisional = rests on a vendor-asserted/unverified claim — do not build on this without verifying first]
```

**Strategist rules:**
- The abstraction must stand on its own. If you removed all mention of the source tool, the concept should still be clear and actionable.
- Be specific about where in behemoth it applies. "Could improve logging" is too vague. "The trader's error handling in `src/shared/logging/` could emit structured error events with `why`/`fix` fields to `.behemoth/events.jsonl`" is concrete.
- Rank concepts by impact: which ones close the biggest gaps or unlock the most value?
- Default to building the pattern, not adopting the dependency, unless the dependency solves a genuinely hard problem (crypto, consensus, etc.)
- **Never rank a concept high-confidence when its load-bearing claim is still `vendor-asserted` or `unverifiable`.** Mark it `provisional` and say what would need to be verified to promote it. A clever pattern built on an unproven number is a liability, not an insight.

**Output**: A ranked list of **abstract patterns** with concrete behemoth application points.

**Gate**: Present to user. Two possible outcomes:

1. **Actionable intel exists** — user confirms concepts worth implementing → chain into `/plan` with the abstracted concepts as the goal. The ABSTRACT output becomes the input context for `/plan`'s EXPLORE phase (which can skip or abbreviate since research already mapped the landscape).

2. **Intel only** — concepts are noted for future reference but no immediate action. Write a research summary to `plans/research-<topic>/BRIEF.md` for later use.

---

## Handoff to /plan

When chaining into `/plan`, pass forward:
- The ranked concept list from ABSTRACT (this is the goal)
- Any specific behemoth files/modules identified as application points (this accelerates EXPLORE)
- Build-vs-buy assessment: borrow the pattern or adopt the dependency?
- **Provenance + confidence per concept**: the source citation and evidence basis. Provisional (vendor-asserted/unverified) premises must be flagged so the plan author knows which premises are solid and which rest on a blog post. `/plan` should verify any provisional *load-bearing* premise before designing on top of it — a plan inherits its premises' confidence.

`/plan` then owns execution from EXPLORE onward. `/research` is done.

**Rules for handoff**:
- Never recommend adopting a tool wholesale without justification. Default to borrowing the pattern, not the dependency.
- If the tool itself is genuinely the right choice (mature, maintained, solves a hard problem), say so — but compare build-vs-buy explicitly.
- If a `/plan` is already active and the concepts fit, propose modifications to the existing plan rather than starting a new one.

---

## Scope Interpretation

| Input | Behavior |
|-------|----------|
| `research <url>` | Full pipeline: SCOUT (+ alternatives scan) → DISSECT+VERIFY → ABSTRACT → (handoff) |
| `research <url> <url>` | SCOUT both, cross-reference in DISSECT |
| `research <topic>` | WebSearch first to find concrete targets, then full pipeline |
| `scout <url>` | SCOUT only — gather, scan alternatives, and present, no analysis or verification |

## Key Behaviors

- **Breadth before depth in SCOUT** — get the full picture (README, source, architecture) before diving into specifics
- **Ideas over implementations in DISSECT** — the tool is a vehicle for concepts, not the point
- **Opus for strategy, sonnet for structure** — comparator extracts, classifies, and verifies; strategist judges value and applicability
- **Concrete over vague in ABSTRACT** — every concept must map to specific behemoth files/modules
- **Build over buy by default** — borrow patterns, not dependencies, unless the dependency is clearly justified
- **Cross-reference when possible** — if multiple sources share a pattern, that signal is stronger
- **Provenance travels** — every claim carries its source and evidence basis from SCOUT through to `/plan`; nothing becomes a premise without it
- **Verify load-bearing claims, classify the rest** — don't launder vendor marketing into fact; spend real verification only where a false claim would flip the decision
- **Scan alternatives even for one target** — counter first-thing-you-looked-at bias; the target's view of its competitors is not neutral
- **Chain, don't duplicate** — research produces intelligence, `/plan` produces implementation. Don't blur the boundary.

## Anti-Patterns

- Recommending a tool adoption without analyzing its concepts first
- Abstracting concepts so generically they become platitudes ("use structured logging")
- Applying concepts that don't fit behemoth's architecture just because they're clever
- Writing implementation plans inside `/research` instead of handing off to `/plan`
- Treating every researched tool as something to install rather than learn from
- Passing a vendor-asserted performance/capability claim downstream as if it were confirmed
- Judging "what makes it different from alternatives" using only the target's own description of its competitors
