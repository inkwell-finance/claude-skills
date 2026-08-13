---
name: worktree-gc
description: Audit and prune accumulated git worktrees without losing work — classify every worktree by dirtiness and branch-liveness, preserve anything uncommitted, push unpushed branches before their checkout disappears, then remove the rest and report space freed. Use after a campaign//squad run, when `git worktree list` is long, when a checkout/push fails with "already checked out in worktree" or "no checkout", or when the user says "clean up worktrees", "worktree gc", "prune worktrees". Never force-removes; dirty worktrees are surfaced, not decided.
argument-hint: "[repo path, default: cwd] [--dry-run]"
---

# Worktree GC

Prune worktree sprawl **without destroying work**. The two failure modes this skill exists to
prevent, both measured on a real run (99 worktrees, 9.3 GB, 2026-08-13):

1. **Pruning a dirty worktree** — one of the 99 held uncommitted research (27 untracked files).
   `rm -rf` would have eaten it silently.
2. **Orphaning an unpushed branch** — pruning first and pushing later fails: two pushes died
   with "no checkout" because the branches lived only in worktrees that were just removed.
   (You *can* push a branch with no checkout via `git push origin <branch>:<branch>` — do it
   BEFORE pruning while the picture is still clear, not as post-failure recovery.)

Order is therefore: **inventory → classify → push → prune → report.** Never reorder.

## 0. Ground rules

- `git worktree remove` only — never `rm -rf` a worktree path. `remove` refuses dirty trees;
  that refusal is the safety mechanism, not an obstacle. `--force` requires the user saying so
  about that specific worktree.
- Uncommitted work is surfaced, never adjudicated. You report it; the human decides.
- If your shell's cwd is inside any worktree being considered, `cd` to the primary checkout
  first — removing the cwd out from under the shell breaks every subsequent command.
- With `--dry-run`, stop after step 2 and print the classification table.

## 1. Inventory

```bash
git worktree list --porcelain   # path / HEAD / branch|detached / locked / prunable per stanza
du -sh <each-worktree-path>     # for the space-freed number; parallelize, tolerate failures
```

The first entry is the primary checkout — exclude it from everything below. Note worktrees
marked `prunable` (path already gone): those need only `git worktree prune`, no inspection.

## 2. Classify every remaining worktree

For each worktree, gather three facts:

```bash
git -C <wt> status --porcelain          # non-empty → DIRTY (staged, modified, or untracked)
git -C <wt> rev-parse --abbrev-ref HEAD  # branch name, or HEAD if detached
# for a branch B: is it unpushed?
git rev-parse --verify --quiet B@{upstream} || echo no-upstream
git rev-list --count B@{upstream}..B 2>/dev/null   # >0 → ahead of upstream
# is B fully contained in the default branch anyway?
git merge-base --is-ancestor B origin/<default> && echo merged
```

Buckets:

| bucket | condition | action |
|---|---|---|
| KEEP | dirty (any uncommitted or untracked files) | preserve; list the files in the report |
| KEEP | locked | preserve; say who/why if the lock has a reason |
| PUSH-THEN-PRUNE | clean, branch ahead of upstream or no upstream (and not merged) | push in step 3, then prune |
| PRUNE | clean, detached HEAD | prune |
| PRUNE | clean, branch merged into default or even with upstream | prune |

A branch survives its worktree's removal — branches are refs, not checkouts. The only thing
lost with a clean worktree is the checkout itself, and the only thing that *needs* the
checkout is nothing, once the branch is pushed.

## 3. Push what would otherwise strand

For every PUSH-THEN-PRUNE branch, from the primary checkout (no checkout of B needed):

```bash
git push origin B:B        # or: git push -u origin B  when it had no upstream
```

A failed push moves that worktree to KEEP with the error attached — never prune a worktree
whose branch you just failed to push.

If the repo has no remote, skip this step and note in the report that unpushed branches
survive as local refs only.

## 4. Prune

```bash
git worktree remove <path>     # per PRUNE / pushed worktree; refuses if it got dirty since step 2
git worktree prune             # clears the prunable stubs
git branch -d <B>              # ONLY for branches confirmed merged in step 2; -d not -D
```

If a `remove` refuses (worktree became dirty between classify and prune), reclassify it as
KEEP — do not escalate to `--force`.

## 5. Report

One table, then the numbers:

- Removed: N worktrees, X GB freed (du before minus after, or sum of removed).
- Pushed first: each branch and its new upstream.
- Kept: each dirty/locked worktree with WHY (file count, lock reason) — these are the ones
  needing a human decision, so they lead the report.
- Deleted branches: only the merged ones, listed.

Close with the one-liner: `result: <N> worktrees removed (<X> freed), <M> kept dirty, <K> branches pushed`.
