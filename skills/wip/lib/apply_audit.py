#!/usr/bin/env python3
"""
apply_audit.py — Apply STATUS flips from an audit JSON to plan-doc concerns.

Input: a JSON array produced by the `/wip triage` audit agents. Each item:
  {
    "path": "plans/.../NN-concern.md",
    "current_status": "open",
    "recommended_status": "done" | "open" | "blocked" | "cancelled",
    "confidence": "high" | "medium" | "low",
    "evidence": "short citation",
    "resolution": "one-line note or null"
  }

What it does for every item with confidence == "high" AND recommended != current:
  1. Rewrite the STATUS line in the concern file:
       `STATUS: open` → `STATUS: done`  (canonical format)
       `**Status:** open.` → `**Status:** done. <resolution suffix>`  (markdown-bold format)
  2. If there's a resolution note AND recommended_status in {done, cancelled},
     append a `## Resolution` section at the end of the file (or update
     existing) citing the evidence + a sync-trail comment.

Usage:
  apply_audit.py <audit.json> [--confidence high,medium] [--dry-run] [--repo <path>]

Safety:
  - Skips items where current_status == recommended_status (no-op).
  - Skips low-confidence by default.
  - --dry-run prints diffs without writing.
  - Refuses to overwrite a file whose STATUS line no longer matches
    current_status (someone else changed it; manual review).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

STATUS_RE_CANONICAL = re.compile(r"^(STATUS:\s*)([\w-]+)", re.MULTILINE)
STATUS_RE_BOLD = re.compile(r"^(\*\*Status:\*\*\s*)([\w-]+)(\.?)", re.MULTILINE | re.IGNORECASE)
RESOLUTION_HEADING_RE = re.compile(r"^##\s+Resolution\b", re.MULTILINE)


def normalize(s: str | None) -> str:
    return (s or "").lower().strip(" .").replace("_", "-")


def rewrite_status(text: str, new_status: str, expected_current: str) -> tuple[str, bool, str]:
    """Rewrite the first STATUS line in the text.

    Returns (new_text, changed, format). `format` is 'canonical' or 'bold' or 'none'.
    If the current on-file status doesn't match expected_current, returns unchanged.
    """
    m_c = STATUS_RE_CANONICAL.search(text)
    if m_c:
        on_file = normalize(m_c.group(2))
        if on_file != normalize(expected_current):
            return text, False, "mismatch"
        new_text = text[: m_c.start(2)] + new_status + text[m_c.end(2):]
        return new_text, True, "canonical"

    m_b = STATUS_RE_BOLD.search(text)
    if m_b:
        on_file = normalize(m_b.group(2))
        if on_file != normalize(expected_current):
            return text, False, "mismatch"
        # Preserve the trailing period if present.
        new_text = text[: m_b.start(2)] + new_status + text[m_b.end(2):]
        return new_text, True, "bold"

    return text, False, "none"


def append_resolution(text: str, resolution: str, evidence: str, plane_ctx: str | None = None) -> str:
    """Append or update a `## Resolution` section.

    If one already exists, insert a new bullet. Otherwise, create the section
    before any trailing sync-trail comments.
    """
    stamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    bullet_lines = [f"- **{stamp}** — {resolution.rstrip('.')}."]
    if evidence:
        bullet_lines.append(f"  - Evidence: {evidence}")
    if plane_ctx:
        bullet_lines.append(f"  - {plane_ctx}")
    bullet = "\n".join(bullet_lines)

    if RESOLUTION_HEADING_RE.search(text):
        # Append a new bullet immediately after the heading's next blank line.
        # Simpler approach: just append to the file end (avoids splitting the section).
        if not text.endswith("\n"):
            text += "\n"
        return text + "\n" + bullet + "\n"

    # Create the section. Insert before trailing sync-trail comments if any.
    sync_trail_anchor = "\n<!-- sync-plans:"
    idx = text.find(sync_trail_anchor)
    section = f"\n\n## Resolution\n\n{bullet}\n"
    if idx != -1:
        return text[:idx] + section + text[idx:]
    if not text.endswith("\n"):
        text += "\n"
    return text + section


def append_sync_trail(text: str, old: str, new: str, evidence: str) -> str:
    stamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    comment = f"\n<!-- wip-triage: STATUS {old} → {new} on {stamp} — {evidence} -->\n"
    if not text.endswith("\n"):
        text += "\n"
    return text + comment


def apply_item(item: dict, repo: Path, dry_run: bool) -> dict:
    rel_path = item["path"]
    abs_path = (repo / rel_path).resolve() if not Path(rel_path).is_absolute() else Path(rel_path).resolve()
    result = {
        "path": rel_path,
        "action": "skip",
        "reason": "",
        "diff": None,
    }

    if not abs_path.exists():
        result["reason"] = "file-missing"
        return result

    current = normalize(item.get("current_status"))
    recommended = normalize(item.get("recommended_status"))
    if current == recommended:
        result["reason"] = "noop"
        return result

    text = abs_path.read_text()
    new_text, changed, fmt = rewrite_status(text, recommended, current)
    if not changed:
        result["reason"] = f"status-mismatch-or-missing ({fmt})"
        return result

    evidence = item.get("evidence") or ""
    resolution = item.get("resolution") or ""
    if recommended in ("done", "closed", "cancelled") and resolution:
        new_text = append_resolution(new_text, resolution, evidence)

    new_text = append_sync_trail(new_text, current, recommended, evidence[:120])

    if dry_run:
        result["action"] = "would-write"
        result["diff"] = f"STATUS: {current} → {recommended}" + (
            f"\n  + Resolution: {resolution}" if resolution else ""
        )
    else:
        abs_path.write_text(new_text)
        result["action"] = "wrote"
        result["diff"] = f"STATUS: {current} → {recommended}"
    return result


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audit_json", help="Path to audit JSON file (array of items)")
    parser.add_argument("--confidence", default="high",
                        help="Comma-separated confidences to apply (default: high)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--repo", default=".",
                        help="Repo root for resolving relative paths")
    args = parser.parse_args(argv)

    audit_path = Path(args.audit_json)
    if not audit_path.exists():
        print(f"ERROR: {audit_path} not found", file=sys.stderr)
        return 1

    items = json.loads(audit_path.read_text())
    if not isinstance(items, list):
        print("ERROR: audit JSON must be an array", file=sys.stderr)
        return 1

    allowed = {c.strip().lower() for c in args.confidence.split(",")}
    repo = Path(args.repo).resolve()

    summary = {"wrote": 0, "would-write": 0, "skip": 0}
    details: list[dict] = []

    for item in items:
        conf = (item.get("confidence") or "").lower()
        if conf not in allowed:
            details.append({"path": item.get("path"), "action": "skip", "reason": f"confidence={conf} not in {allowed}"})
            summary["skip"] += 1
            continue
        r = apply_item(item, repo, args.dry_run)
        details.append(r)
        summary[r["action"]] += 1

    # Report.
    print(f"\n=== apply_audit ({'dry-run' if args.dry_run else 'write'}) ===")
    print(f"allowed confidences: {sorted(allowed)}")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print()
    for d in details:
        if d["action"] in ("wrote", "would-write"):
            print(f"  [{d['action']}] {d['path']}")
            if d.get("diff"):
                for line in d["diff"].splitlines():
                    print(f"      {line}")
        elif d.get("reason") and d["reason"] not in ("noop", ):
            print(f"  [skip:{d['reason']}] {d['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
