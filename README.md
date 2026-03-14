# Claude Skills

Reusable Claude Code skills for software engineering workflows.

## Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| [remediate](skills/remediate/) | `/remediate` | Reactive: gap analysis → structured plans → batched parallel execution → audit |
| [plan](skills/plan/) | `/plan` | Proactive: goal decomposition → design → batched parallel execution → audit |

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

Both skills follow the same execution model:

1. **Analysis** — parallel agents explore the codebase
2. **Planning** — structured concern files with dependency graphs
3. **Execution** — batched parallel agents with model-appropriate assignment (haiku/sonnet/opus)
4. **Audit** — mandatory re-analysis of changes, catches multi-agent conflicts
5. **Calibration** — learnings rewrite the skill file itself (`/remediate calibrate` or `/plan calibrate`)

### Model Assignment

| COMPLEXITY tag | Model | Use when |
|----------------|-------|----------|
| `mechanical` | haiku | Schema fix, config, boilerplate, < 10 files |
| `architectural` | sonnet | Cross-repo, system integration, 10+ files |
| `research` | opus | Single most critical design decision per run |

### Key Concepts

- **TOUCHES**: each concern declares which files it modifies. Overlapping TOUCHES can't parallelize.
- **BLOCKED_BY + VERIFY_BLOCKER**: dependencies include a concrete check to verify the blocker is real at execution time.
- **Context propagation**: later agents receive summaries of what earlier agents changed in shared files.
- **Cross-repo contracts**: agents implementing against interfaces in other repos receive the current type signatures.
- **Calibration loop**: audit findings become rules → rules rewrite the skill → next run's agents behave differently.
