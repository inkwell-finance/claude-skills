#!/usr/bin/env python3
"""
scan.py — Enumerate in-flight plan work under a search directory.

Scans for two plan-doc conventions:

1. /plan directories: <search>/plans/<name>/NN-*.md
   Concern file header: "STATUS: <state>" as a top-level line.

2. Flat plan docs: <search>/packages/*/plans/*.md (and similar),
   Concern file header: "**Status:** <state>" as markdown-bold prose.

For each concern it extracts:
  - STATUS (open | in-progress | closed | done | blocked | cancelled | unknown)
  - PRIORITY (p0 | p1 | p2 | none)
  - MODE (hitl | afk; absent -> afk; unrecognized -> hitl, fail-closed, plus a warning)
  - PLANE pointer (e.g. "DAGON-9" from a "PLANE: DAGON-NN ..." line)
  - mtime (fs modification time)
  - title (first H1)

Each /plan directory's 00-overview.md is also read once for two aggregate
signals: `has_fog` (a "## Not yet specified" section with a real bullet, i.e.
not just the canonical "- (none)" marker) and `design_pending`
("## Notes" containing "DECOMPOSE: pending"). A dir with either signal stays
in the scan even if it has zero concern files. `plan_is_open()` is the single
definition of plan open-ness (open concerns, fog, or design-pending) shared by
ranking and both emitters.

Aggregates per plan and emits JSON on stdout.

Usage:
  scan.py <search-dir> [--format json|summary] [--include-archive]

Exit codes:
  0  success
  1  search-dir missing
  2  malformed concern file (reported, but doesn't abort)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


STATUS_RE_CANONICAL = re.compile(r"^STATUS:\s*([\w-]+)", re.MULTILINE)
STATUS_RE_BOLD = re.compile(r"^\*\*Status:\*\*\s*([\w-]+)", re.MULTILINE | re.IGNORECASE)
# H2 heading variant: `## Status: 🟢 Complete` — emoji + free-form word. We extract the
# first identifier-word after any emoji/punctuation prefix.
STATUS_RE_H2 = re.compile(r"^##\s*Status:\s*(?:[^\w\s]+\s*)?([\w-]+)", re.MULTILINE | re.IGNORECASE)
PRIORITY_RE = re.compile(r"^PRIORITY:\s*(p[0-3])", re.MULTILINE | re.IGNORECASE)
PLANE_RE = re.compile(r"^PLANE:\s*([A-Z]+-\d+)", re.MULTILINE)
TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)

# MODE mirrors the two STATUS conventions (canonical + bold); no H2 variant needed.
MODE_RE_CANONICAL = re.compile(r"^MODE:\s*([\w-]+)", re.MULTILINE)
MODE_RE_BOLD = re.compile(r"^\*\*Mode:\*\*\s*([\w-]+)", re.MULTILINE | re.IGNORECASE)
VALID_MODES = {"hitl", "afk"}

# Fog / decompose-pending detection inside 00-overview.md.
NOT_YET_SPECIFIED_RE = re.compile(r"^##\s*Not yet specified\s*$", re.MULTILINE | re.IGNORECASE)
NOTES_HEADING_RE = re.compile(r"^##\s*Notes\s*$", re.MULTILINE | re.IGNORECASE)
DECOMPOSE_PENDING_RE = re.compile(r"^DECOMPOSE:\s*pending", re.MULTILINE | re.IGNORECASE)
FOG_EMPTY_MARKER_RE = re.compile(r"^-\s*\(none\)\s*$", re.IGNORECASE)

# Statuses we consider still-in-flight (the things a WIP counter should surface).
OPEN_STATUSES = {"open", "in-progress", "in_progress", "inprogress", "blocked", "unknown"}
CLOSED_STATUSES = {"closed", "done", "complete", "completed", "cancelled", "canceled"}

# Files that aren't concerns — landscape / design / archive.
SKIP_BASENAMES = {
    "00-overview.md",
    "overview.md",
    "design.md",
    "DESIGN.md",
    "README.md",
    "CALIBRATION.md",
    "CEO-PLAN.md",
    "POSITIONING.md",
    "OUTREACH.md",
    "UNIT-ECONOMICS.md",
    "UI-SPEC.md",
}


def normalize_status(raw: str | None) -> str:
    if not raw:
        return "unknown"
    s = raw.lower().strip(" .")
    return s.replace("_", "-")


def parse_concern(path: Path) -> dict | None:
    try:
        text = path.read_text(errors="replace")
    except OSError as e:
        print(f"WARN: cannot read {path}: {e}", file=sys.stderr)
        return None

    m_canonical = STATUS_RE_CANONICAL.search(text)
    m_bold = STATUS_RE_BOLD.search(text)
    m_h2 = STATUS_RE_H2.search(text)
    status_raw = (m_canonical.group(1) if m_canonical
                  else m_bold.group(1) if m_bold
                  else m_h2.group(1) if m_h2
                  else None)

    # A file with no STATUS at all is probably a doc, not a concern. Skip silently.
    if status_raw is None:
        return None

    prio = PRIORITY_RE.search(text)
    plane = PLANE_RE.search(text)
    title = TITLE_RE.search(text)
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

    m_mode_canonical = MODE_RE_CANONICAL.search(text)
    m_mode_bold = MODE_RE_BOLD.search(text)
    mode_raw = (m_mode_canonical.group(1) if m_mode_canonical
                else m_mode_bold.group(1) if m_mode_bold
                else None)

    warnings: list[str] = []
    if mode_raw is None:
        mode = "afk"
    else:
        mode_norm = mode_raw.lower().strip(" .")
        if mode_norm in VALID_MODES:
            mode = mode_norm
        else:
            # Fail closed: an unrecognized MODE must not unlock autonomous dispatch.
            mode = "hitl"
            warnings.append(f"MODE: unrecognized value {mode_raw!r} — treating as hitl (fail-closed)")

    return {
        "path": str(path),
        "title": title.group(1) if title else path.stem,
        "status": normalize_status(status_raw),
        "priority": prio.group(1).lower() if prio else "none",
        "plane_id": plane.group(1) if plane else None,
        "mtime": mtime.isoformat(timespec="seconds"),
        "mode": mode,
        "warnings": warnings,
    }


def iter_candidate_files(plan_dir: Path, include_archive: bool) -> Iterable[Path]:
    """Yield candidate concern files within a plan directory (recursive one level)."""
    for p in plan_dir.iterdir():
        if p.is_dir():
            if p.name == "archive" and not include_archive:
                continue
            # One-level recurse for sub-plans (e.g. dagon/plans/dagon-dark-pool/build/).
            for sub in p.glob("*.md"):
                if sub.name in SKIP_BASENAMES:
                    continue
                yield sub
            continue
        if p.suffix != ".md":
            continue
        if p.name in SKIP_BASENAMES:
            continue
        yield p


def _extract_section(text: str, heading_re: re.Pattern[str]) -> str | None:
    """Return the body of a `## Heading` section, up to the next H1/H2 heading."""
    m = heading_re.search(text)
    if m is None:
        return None
    start = m.end()
    next_heading = re.search(r"^#{1,2}\s", text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def parse_overview(path: Path) -> dict:
    """Parse a plan dir's 00-overview.md for fog and decompose-pending signals.

    `has_fog`: the `## Not yet specified` section exists and contains at least
    one bullet that isn't the canonical empty marker `- (none)`.
    `design_pending`: the `## Notes` section contains `DECOMPOSE: pending`.
    Missing file or missing sections are not errors — both fields default False.
    """
    result = {"has_fog": False, "design_pending": False}
    if not path.is_file():
        return result
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return result

    fog_section = _extract_section(text, NOT_YET_SPECIFIED_RE)
    if fog_section is not None:
        for line in fog_section.splitlines():
            line = line.strip()
            if not line.startswith("-"):
                continue
            if FOG_EMPTY_MARKER_RE.match(line):
                continue
            result["has_fog"] = True
            break

    notes_section = _extract_section(text, NOTES_HEADING_RE)
    if notes_section is not None and DECOMPOSE_PENDING_RE.search(notes_section):
        result["design_pending"] = True

    return result


def discover_plan_roots(search_dir: Path) -> list[Path]:
    """Return all directories literally named 'plans' under search_dir."""
    return sorted(p for p in search_dir.rglob("plans") if p.is_dir() and "node_modules" not in p.parts)


def scan_plan_root(plans_root: Path, include_archive: bool) -> list[dict]:
    """Scan one `plans/` root and return per-plan aggregates.

    A "plan" is either:
      - a subdirectory of `plans/` (canonical /plan format), OR
      - a flat `.md` file directly under `plans/` (ad-hoc concern).
    Each gets one aggregate row.
    """
    plans = []

    # 1. Flat concern files directly under plans/.
    for flat in plans_root.glob("*.md"):
        if flat.name in SKIP_BASENAMES:
            continue
        c = parse_concern(flat)
        if c is None:
            continue
        plans.append(_build_plan_row(
            name=flat.stem,
            path=flat,
            kind="flat",
            concerns=[c],
        ))

    # 2. Subdirectory plans.
    for sub in sorted(p for p in plans_root.iterdir() if p.is_dir()):
        if sub.name == "archive" and not include_archive:
            continue
        concerns = [parse_concern(f) for f in iter_candidate_files(sub, include_archive)]
        concerns = [c for c in concerns if c is not None]
        overview = parse_overview(sub / "00-overview.md")
        # A dir with fog or a pending decompose is still open even with zero
        # concern files — don't drop it from the scan.
        if not concerns and not overview["has_fog"] and not overview["design_pending"]:
            continue
        concerns.sort(key=lambda c: c["path"])
        plans.append(_build_plan_row(
            name=sub.name,
            path=sub,
            kind="directory",
            concerns=concerns,
            has_fog=overview["has_fog"],
            design_pending=overview["design_pending"],
        ))

    return plans


def _build_plan_row(name: str, path: Path, kind: str, concerns: list[dict],
                    has_fog: bool = False, design_pending: bool = False) -> dict:
    status_counts = Counter(c["status"] for c in concerns)
    open_count = sum(status_counts[s] for s in OPEN_STATUSES if s in status_counts)
    closed_count = sum(status_counts[s] for s in CLOSED_STATUSES if s in status_counts)
    hitl_open = sum(1 for c in concerns if c["status"] in OPEN_STATUSES and c.get("mode") == "hitl")
    promoted = sum(1 for c in concerns if c["plane_id"])
    if concerns:
        mtimes = [c["mtime"] for c in concerns]
        oldest_mtime = min(mtimes)
        newest_mtime = max(mtimes)
    else:
        # Concern-less fog/design-pending dir: fall back to the dir's own mtime.
        fallback = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")
        oldest_mtime = newest_mtime = fallback
    return {
        "name": name,
        "path": str(path),
        "kind": kind,
        "concern_count": len(concerns),
        "open_count": open_count,
        "closed_count": closed_count,
        "hitl_open": hitl_open,
        "has_fog": has_fog,
        "design_pending": design_pending,
        "by_status": dict(status_counts),
        "oldest_mtime": oldest_mtime,
        "newest_mtime": newest_mtime,
        "promoted_to_plane": promoted,
        "concerns": concerns,
    }


def plan_is_open(row: dict) -> bool:
    """Single definition of plan open-ness, used by ranking and both emitters.

    A plan is open if it has open concerns, OR it has fog (unresolved
    `## Not yet specified` items), OR its overview is DECOMPOSE-pending —
    even a plan with zero or all-closed concern files stays visible in
    that case.
    """
    return row["open_count"] > 0 or row.get("has_fog", False) or row.get("design_pending", False)


def rank_plans(plans: list[dict]) -> list[dict]:
    """Sort so the plans most worth finishing surface first.

    Heuristic: plans with the *most* open concerns and the oldest activity
    sort first. Fully-closed plans sink. Ties broken by promoted-count (more
    promoted = closer to the agent-handoff line = cheaper to finish).
    """
    def key(p):
        has_open = 1 if plan_is_open(p) else 0
        return (
            -has_open,              # still-open plans first
            -p["open_count"],       # more open concerns → earlier (counterintuitive, but "most work remaining" = most valuable to finish)
            p["oldest_mtime"],      # oldest activity first (stale = priority)
            -p["promoted_to_plane"],
        )
    return sorted(plans, key=key)


def emit_json(plans: list[dict], search_dir: Path) -> None:
    out = {
        "scanned_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "search_dir": str(search_dir),
        "totals": {
            "plans": len(plans),
            "open_plans": sum(1 for p in plans if plan_is_open(p)),
            "concerns": sum(p["concern_count"] for p in plans),
            "open_concerns": sum(p["open_count"] for p in plans),
            "closed_concerns": sum(p["closed_count"] for p in plans),
            "promoted_concerns": sum(p["promoted_to_plane"] for p in plans),
            "hitl_open_concerns": sum(p["hitl_open"] for p in plans),
            "plans_with_fog": sum(1 for p in plans if p.get("has_fog")),
            "plans_design_pending": sum(1 for p in plans if p.get("design_pending")),
        },
        "plans": plans,
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


def emit_summary(plans: list[dict], search_dir: Path) -> None:
    open_plans = [p for p in plans if plan_is_open(p)]
    total_open = sum(p["open_count"] for p in plans)
    total_closed = sum(p["closed_count"] for p in plans)
    total_promoted = sum(p["promoted_to_plane"] for p in plans)
    total_hitl_open = sum(p["hitl_open"] for p in plans)

    print(f"# WIP under {search_dir}")
    print(f"  {len(plans)} plans, {len(open_plans)} with open work")
    print(f"  {total_open} open concerns, {total_closed} closed, {total_promoted} promoted to Plane")
    if total_hitl_open:
        print(f"  {total_hitl_open} hitl — waiting on you")
    print()
    if not open_plans:
        print("  (nothing open — clean slate.)")
        return
    print(f"{'plan':<40} {'open':>5} {'closed':>7} {'plane':>6} {'oldest':>11}")
    print("-" * 72)
    for p in open_plans:
        oldest = p["oldest_mtime"][:10]
        loc = _locate_marker(p["path"])
        line = f"{loc:<40} {p['open_count']:>5} {p['closed_count']:>7} {p['promoted_to_plane']:>6} {oldest:>11}"
        notes = []
        if p["hitl_open"]:
            notes.append(f"{p['hitl_open']} hitl — waiting on you")
        if p.get("has_fog"):
            notes.append("fog present")
        if p.get("design_pending"):
            notes.append("design pending")
        if notes:
            line += "  (" + ", ".join(notes) + ")"
        print(line)


def _locate_marker(path_str: str) -> str:
    """Compact label for the summary: `<location>/<name>`."""
    p = Path(path_str)
    for i, part in enumerate(p.parts):
        if part == "plans":
            prefix = p.parts[i - 1] if i > 0 else "."
            name = "/".join(p.parts[i + 1:]) or p.name
            return f"{prefix}:{name}"
    return p.name


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("search_dir", nargs="?", default=".", help="Directory to scan (default: cwd)")
    parser.add_argument("--format", choices=["json", "summary"], default="json")
    parser.add_argument("--include-archive", action="store_true",
                        help="Include plans/archive/ directories in the scan")
    parser.add_argument("--rank", action="store_true",
                        help="Sort plans by the resume-worth heuristic before emitting")
    args = parser.parse_args(argv)

    search_dir = Path(args.search_dir).resolve()
    if not search_dir.is_dir():
        print(f"ERROR: {search_dir} is not a directory", file=sys.stderr)
        return 1

    roots = discover_plan_roots(search_dir)
    all_plans: list[dict] = []
    for root in roots:
        all_plans.extend(scan_plan_root(root, args.include_archive))

    if args.rank:
        all_plans = rank_plans(all_plans)

    if args.format == "json":
        emit_json(all_plans, search_dir)
    else:
        emit_summary(all_plans, search_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
