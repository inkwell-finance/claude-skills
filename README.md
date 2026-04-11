# Claude Skills

## What is this?

These skills encode the workflows we've developed through repeated use of Claude Code on real projects. Rather than re-explaining the same multi-agent patterns each conversation, we captured them as reusable skill files that Claude Code can invoke directly.

The core loop we kept arriving at: analyze the problem space, produce structured plans with dependency graphs, fan out to parallel agents with the right model for each task, then audit everything the agents did. Each skill is a variation on that loop — `/remediate` for fixing what's broken, `/plan` for building something new, `/prioritize` for figuring out what to do next.

The skills also self-improve. A calibration step after each run bakes audit findings back into the skill file, so mistakes from one run become rules for the next.

## Skills

| Skill | Command | Trigger | Purpose |
|-------|---------|---------|---------|
| [remediate](skills/remediate/) | `/remediate` | Something is broken | Gap analysis → structured plans → batched parallel execution → audit |
| [plan](skills/plan/) | `/plan` | Something needs to be built | Goal decomposition → design → batched parallel execution → audit |
| [prioritize](skills/prioritize/) | `/prioritize` | What should we build next? | Audit plans vs code → verify status → discover gaps → score → rank |
| [research](skills/research/) | `/research` | External tool/concept to evaluate | Scout → dissect → abstract → chain to `/plan` if actionable |
| [leviathan-agent](skills/leviathan-agent/) | `/leviathan-agent` | Stake IKA, analyze validators, manage API keys | IKA staking API client: allocate → build tx → sign → submit |
| [sol-faucet](skills/sol-faucet/) | `/sol-faucet` | Need devnet/testnet SOL | Browser automation for faucet.solana.com with persistent GitHub auth |

## Installation

### Personal (all projects)
```bash
cp -r skills/* ~/.claude/skills/
```

### Project-specific
```bash
cp -r skills/* .claude/skills/
```

## How They Work

### Execution Models

**`/remediate`** — Reactive pipeline for finding and fixing issues:
```
ANALYZE → PLAN → EXECUTE → AUDIT → (loop if issues found) → CLOSE
```

**`/plan`** — Proactive pipeline for building new things:
```
EXPLORE → DESIGN → DECOMPOSE → (optional) EXECUTE → AUDIT → CLOSE
```

**`/prioritize`** — Audit pipeline for deciding what to work on next:
```
INVENTORY → VERIFY → DISCOVER → SCORE → RANK → PRESENT
```

**`/research`** — Intelligence gathering pipeline for external tools, libraries, and concepts:
```
SCOUT → DISSECT → ABSTRACT → (chain to /plan if actionable)
```

All four skills use **gated phases** — they pause for user confirmation before advancing to the next phase.

### Model Assignment

Each concern/task declares a COMPLEXITY tag that determines which model executes it:

| COMPLEXITY tag | Model | Use when |
|----------------|-------|----------|
| `mechanical` | haiku | Schema fix, config, boilerplate, < 10 files |
| `architectural` | sonnet | Cross-repo, system integration, 10+ files |
| `research` | opus | Single most critical design decision per run |

### Key Concepts

- **Concern files**: Structured markdown files describing a unit of work (problem/goal, approach, verification steps, metadata like TOUCHES, COMPLEXITY, BLOCKED_BY)
- **TOUCHES**: Each concern declares which files it modifies. Overlapping TOUCHES can't parallelize — they go to the same agent or sequential batches.
- **BLOCKED_BY + VERIFY_BLOCKER**: Dependencies include a concrete 30s check to confirm the blocker is real at execution time. False blockers get promoted.
- **Context propagation**: Later agents receive summaries of what earlier agents changed in shared files.
- **Cross-repo contracts**: Agents implementing against interfaces in other repos receive the current type signatures.
- **Calibration loop**: Audit findings become rules → `/remediate calibrate` or `/plan calibrate` rewrites the skill file itself → next run's agents behave differently.

### Plan Structure

```
plans/<name>/
├── DESIGN.md           # Architectural decisions (/plan only)
├── 00-overview.md      # Scope, deps, batch order
├── 01-concern.md       # First task
├── 02-concern.md       # Second task
└── ...

plans/
├── README.md           # Plan index with status tracking
├── CONVENTIONS.md      # File format, lifecycle, resolution rules
├── DEPENDENCIES.md     # Cross-plan dependency graph + batch plan
└── CALIBRATION.md      # Learnings and rules from prior runs
```

### Scope Inputs

Each skill accepts scope arguments to skip phases or target specific plans:

| Skill | Input | Behavior |
|-------|-------|----------|
| `/remediate` | `all` | Full pipeline: analyze all repos |
| `/remediate` | `repos/<name>` | Analyze single repo |
| `/remediate` | `plans/` | Skip analysis, execute existing plans |
| `/remediate` | `audit` | Skip to audit phase on recent changes |
| `/remediate` | `calibrate` | Bake CALIBRATION.md rules into the skill |
| `/plan` | `<goal>` | Full pipeline: explore → design → decompose |
| `/plan` | `plans/<name>` | Execute existing plan |
| `/plan` | `audit` | Skip to audit phase |
| `/plan` | `calibrate` | Bake CALIBRATION.md rules into the skill |
| `/prioritize` | (no args) | Full audit: all plans + codebase scan |
| `/prioritize` | `plans` | Plans-only: inventory + verify, skip discovery |
| `/prioritize` | `gaps` | Gaps-only: skip plans, scan code for issues |
| `/prioritize` | `quick` | Fast mode: inventory + verify only |
| `/research` | `<url>` | Full pipeline: scout → dissect → abstract |
| `/research` | `<url> <url>` | Scout both, cross-reference in dissect |
| `/research` | `<topic>` | WebSearch first, then full pipeline |
| `/research` | `scout <url>` | Scout only — gather and present, no analysis |
