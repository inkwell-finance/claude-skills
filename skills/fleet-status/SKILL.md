---
name: fleet-status
description: One-shot live status ledger for an omp-squad fleet run — roster, PRs, plan WIP, and land-blockers in three buckets (HELD on a human / QUEUED behind a dependency / SHIPPED as a PR). Use when the user asks "status", "fleet status", "what's the fleet doing", "what is still being worked on", "what's left", or wants a snapshot mid- or post-squad-run. Read-only — it never dispatches, prompts, kills, or lands anything; use /squad for that.
argument-hint: "[repo path, default: cwd]"
---

# Fleet Status

Answer one question in one pass: **what is held on a human, what is queued behind something, and what has shipped.** Read-only. If the user asks "status" during a squad run, this is the skill — do not hand-assemble a recap from memory.

## 1. Gather (all four in parallel; each degrades gracefully)

1. **Roster — JSON, never the text view** (the text roster misparses into duplicate columns):
   ```bash
   omp-squad list --json     # binary lives at ~/.bun/bin/omp-squad if not on PATH
   ```
   Per agent: `id`, `name`, `status` (`working` | `idle` | `input` | `error`), `repo`, `branch`, `pending` (unanswered prompts), `issue.blockedBy`, `kind`. Filter to the target repo. Empty roster or connection refused → say "no daemon / no fleet agents" and continue with the other sources — PRs and plan WIP still answer most of the question. Do NOT start a daemon. A throwaway fleet may live on another port: check `$OMP_SQUAD_PORT` / `--port`.
2. **Land-blockers:**
   ```bash
   omp-squad doctor --json
   ```
   Surface only `warn`/`error` checks that block lands (e.g. `repo.<name>.dirty` — "every land will refuse, and retry forever"). Ignore cosmetic warnings.
3. **PRs (shipped + in-review):**
   ```bash
   gh pr list --state open --json number,title,headRefName,isDraft
   gh pr list --state merged --limit 10 --json number,title,mergedAt
   ```
   Match roster branches to `headRefName` to link agents to their PRs. Remember cross-fork topology: PRs may live on `origin` while pushes go to `fork` — `gh pr list` in the repo already targets the right one.
4. **Plan WIP** (only if a `plans/` dir exists):
   ```bash
   python3 ~/.claude/skills/wip/lib/scan.py <repo-root> --format summary --rank
   ```

## 2. Bucket

- **HELD (a human must act):** agent `status` = `input` or `error`, or non-empty `pending`; PRs awaiting the user's review/merge decision; doctor land-blockers (dirty repo = every green agent is stuck behind it — say so explicitly).
- **QUEUED (waiting on something automatic):** `issue.blockedBy` unmet, unit sequenced behind another's land, park-queue entries, agents `working` (in-flight is queued-on-itself — show them here with what they're building).
- **SHIPPED:** open PR per landed/pushed branch (number + title + draft?), plus merges since the last status ask.

An `idle` agent with a clean tree and a PR up is SHIPPED; `idle` with a dirty worktree is HELD ("finished but didn't commit" — the classic wrapper failure mode).

## 3. Report

Lead with one verdict line: `N held on you · N in flight/queued · N shipped`. Then one line per unit — name, bucket reason, PR# where linked. Held items first, each with the exact unblock action (answer prompt X, review PR #Y, commit/stash the dirty tree). Terse; no tables unless the fleet is large (>10 units). If everything is quiet, say so in two lines — don't pad.

## Hard rules

- Read-only: never `prompt`, `kill`, `rm`, `add`, or land from this skill. Recommend the action; `/squad` executes it.
- Never start or restart a daemon here — report its absence instead.
- One terminal per daemon still applies: `list`/`doctor` are safe reads, but do not attach a second monitor loop to a daemon another terminal is driving.
