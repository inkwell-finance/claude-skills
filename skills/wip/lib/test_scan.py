#!/usr/bin/env python3
"""
test_scan.py — stdlib unittest suite for scan.py.

Run:
  python3 ~/.claude/skills/wip/lib/test_scan.py

These tests build synthetic plan directories in a tempdir and verify the
scanner's outputs match the documented contract. They don't touch the real
inkwell repo.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import scan  # noqa: E402


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wip-test-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def _write(self, rel: str, body: str) -> Path:
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(body).lstrip())
        return p

    def test_parses_canonical_status(self):
        p = self._write("c.md", """
            # Something
            STATUS: open
            PRIORITY: p1
            """)
        c = scan.parse_concern(p)
        self.assertEqual(c["status"], "open")
        self.assertEqual(c["priority"], "p1")

    def test_parses_bold_markdown_status(self):
        p = self._write("c.md", """
            # Something
            **Status:** closed. Shipped 2026-04-01.
            """)
        c = scan.parse_concern(p)
        self.assertEqual(c["status"], "closed")

    def test_parses_h2_status_with_emoji(self):
        p = self._write("c.md", """
            # Something
            ## Status: 🟢 Complete
            """)
        c = scan.parse_concern(p)
        self.assertEqual(c["status"], "complete")

    def test_parses_h2_status_plain(self):
        p = self._write("c.md", """
            # Something
            ## Status: in-progress
            """)
        c = scan.parse_concern(p)
        self.assertEqual(c["status"], "in-progress")

    def test_canonical_status_wins_over_h2(self):
        # If a file somehow has both, canonical is first-match per the regex order.
        p = self._write("c.md", """
            # Something
            STATUS: open
            ## Status: Complete
            """)
        c = scan.parse_concern(p)
        self.assertEqual(c["status"], "open")

    def test_status_normalization(self):
        cases = [("in-progress", "in-progress"), ("in_progress", "in-progress"),
                 ("Done.", "done"), ("OPEN", "open"), ("Closed", "closed")]
        for raw, normalized in cases:
            self.assertEqual(scan.normalize_status(raw), normalized, raw)

    def test_skips_file_with_no_status(self):
        p = self._write("c.md", """
            # Design doc — no status line

            Some narrative prose.
            """)
        self.assertIsNone(scan.parse_concern(p))

    def test_extracts_plane_pointer(self):
        p = self._write("c.md", """
            # X
            STATUS: open
            PLANE: DAGON-9 — https://app.plane.so/inkwell-finance/browse/DAGON-9/
            """)
        c = scan.parse_concern(p)
        self.assertEqual(c["plane_id"], "DAGON-9")

    def test_missing_plane_pointer_is_none(self):
        p = self._write("c.md", """
            # X
            STATUS: open
            """)
        c = scan.parse_concern(p)
        self.assertIsNone(c["plane_id"])

    def test_title_extraction(self):
        p = self._write("c.md", """
            # The Real Title

            STATUS: open
            """)
        c = scan.parse_concern(p)
        self.assertEqual(c["title"], "The Real Title")

    def test_mode_absent_defaults_afk(self):
        p = self._write("c.md", """
            # X
            STATUS: open
            """)
        c = scan.parse_concern(p)
        self.assertEqual(c["mode"], "afk")
        self.assertEqual(c["warnings"], [])

    def test_mode_canonical(self):
        p = self._write("c.md", """
            # X
            STATUS: open
            MODE: hitl
            """)
        c = scan.parse_concern(p)
        self.assertEqual(c["mode"], "hitl")
        self.assertEqual(c["warnings"], [])

    def test_mode_canonical_afk(self):
        p = self._write("c.md", """
            # X
            STATUS: open
            MODE: afk
            """)
        c = scan.parse_concern(p)
        self.assertEqual(c["mode"], "afk")

    def test_mode_bold(self):
        p = self._write("c.md", """
            # X
            STATUS: open
            **Mode:** hitl
            """)
        c = scan.parse_concern(p)
        self.assertEqual(c["mode"], "hitl")
        self.assertEqual(c["warnings"], [])

    def test_mode_case_insensitive(self):
        p = self._write("c.md", """
            # X
            STATUS: open
            MODE: HITL
            """)
        c = scan.parse_concern(p)
        self.assertEqual(c["mode"], "hitl")

    def test_mode_typo_fails_closed_to_hitl_with_warning(self):
        # "hilt" instead of "hitl" — the exact typo the fail-closed rule exists for.
        p = self._write("c.md", """
            # X
            STATUS: open
            MODE: hilt
            """)
        c = scan.parse_concern(p)
        self.assertEqual(c["mode"], "hitl")
        self.assertEqual(len(c["warnings"]), 1)
        self.assertIn("hilt", c["warnings"][0])


class OverviewFogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wip-fog-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def _write(self, rel: str, body: str) -> Path:
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(body).lstrip())
        return p

    def test_missing_overview_has_no_fog(self):
        result = scan.parse_overview(self.tmp / "nope.md")
        self.assertFalse(result["has_fog"])
        self.assertFalse(result["design_pending"])

    def test_empty_marker_is_not_fog(self):
        p = self._write("00-overview.md", """
            # Overview

            ## Not yet specified

            - (none)

            ## Notes
            """)
        result = scan.parse_overview(p)
        self.assertFalse(result["has_fog"])

    def test_real_bullet_is_fog(self):
        p = self._write("00-overview.md", """
            # Overview

            ## Not yet specified

            - Should the daemon read labels at all?

            ## Notes
            """)
        result = scan.parse_overview(p)
        self.assertTrue(result["has_fog"])

    def test_decompose_pending_under_notes(self):
        p = self._write("00-overview.md", """
            # Overview

            ## Not yet specified

            - (none)

            ## Notes

            DECOMPOSE: pending
            """)
        result = scan.parse_overview(p)
        self.assertTrue(result["design_pending"])
        self.assertFalse(result["has_fog"])

    def test_no_decompose_line_is_not_pending(self):
        p = self._write("00-overview.md", """
            # Overview

            ## Notes

            Some narrative notes, nothing pending.
            """)
        result = scan.parse_overview(p)
        self.assertFalse(result["design_pending"])


class FogAggregationTests(unittest.TestCase):
    """scan_plan_root / plan_is_open with fog and design-pending signals."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wip-fog-agg-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def _plan(self, name: str, concerns: list[tuple[str, str]]):
        d = self.tmp / "plans" / name
        d.mkdir(parents=True, exist_ok=True)
        for fn, body in concerns:
            (d / fn).write_text(textwrap.dedent(body).lstrip())
        return d

    def test_typod_mode_counts_as_hitl_open(self):
        self._plan("p1", [
            ("01-a.md", "# A\nSTATUS: open\nMODE: hilt\n"),
            ("02-b.md", "# B\nSTATUS: open\nMODE: afk\n"),
        ])
        plans = scan.scan_plan_root(self.tmp / "plans", include_archive=False)
        p = plans[0]
        self.assertEqual(p["hitl_open"], 1)

    def test_closed_hitl_concern_not_counted(self):
        # A hitl concern that's already closed shouldn't inflate "waiting on you".
        self._plan("p1", [
            ("01-a.md", "# A\nSTATUS: closed\nMODE: hitl\n"),
        ])
        plans = scan.scan_plan_root(self.tmp / "plans", include_archive=False)
        self.assertEqual(plans[0]["hitl_open"], 0)

    def test_fog_only_dir_with_zero_concerns_still_emits(self):
        d = self.tmp / "plans" / "foggy"
        d.mkdir(parents=True, exist_ok=True)
        (d / "00-overview.md").write_text(textwrap.dedent("""
            # Foggy Plan

            ## Not yet specified

            - What's the storage backend?

            ## Notes
            """).lstrip())
        plans = scan.scan_plan_root(self.tmp / "plans", include_archive=False)
        self.assertEqual(len(plans), 1)
        p = plans[0]
        self.assertEqual(p["concern_count"], 0)
        self.assertTrue(p["has_fog"])
        self.assertTrue(scan.plan_is_open(p))

    def test_design_pending_only_dir_with_zero_concerns_still_emits(self):
        d = self.tmp / "plans" / "pending-decompose"
        d.mkdir(parents=True, exist_ok=True)
        (d / "00-overview.md").write_text(textwrap.dedent("""
            # Pending Decompose

            ## Not yet specified

            - (none)

            ## Notes

            DECOMPOSE: pending
            """).lstrip())
        plans = scan.scan_plan_root(self.tmp / "plans", include_archive=False)
        self.assertEqual(len(plans), 1)
        p = plans[0]
        self.assertEqual(p["concern_count"], 0)
        self.assertTrue(p["design_pending"])
        self.assertTrue(scan.plan_is_open(p))

    def test_dir_with_no_concerns_no_fog_no_pending_is_dropped(self):
        d = self.tmp / "plans" / "empty"
        d.mkdir(parents=True, exist_ok=True)
        (d / "00-overview.md").write_text("# Empty\n\n## Not yet specified\n\n- (none)\n")
        plans = scan.scan_plan_root(self.tmp / "plans", include_archive=False)
        self.assertEqual(len(plans), 0)

    def test_all_closed_with_real_fog_still_open(self):
        d = self._plan("has-fog-all-closed", [
            ("01-a.md", "# A\nSTATUS: closed\n"),
            ("02-b.md", "# B\nSTATUS: done\n"),
        ])
        (d / "00-overview.md").write_text(textwrap.dedent("""
            # Has Fog All Closed

            ## Not yet specified

            - Unresolved question remains.
            """).lstrip())
        plans = scan.scan_plan_root(self.tmp / "plans", include_archive=False)
        p = plans[0]
        self.assertEqual(p["open_count"], 0)
        self.assertTrue(p["has_fog"])
        self.assertTrue(scan.plan_is_open(p))


class WayfinderEndToEndTests(unittest.TestCase):
    """Full fixture root covering every Approach item, run through the CLI."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wip-wayfinder-e2e-"))

        # Plan with canonical + bold MODE, a typo'd MODE (hitl+warning).
        modes = self.tmp / "plans" / "modes-plan"
        modes.mkdir(parents=True)
        (modes / "01-canonical.md").write_text("# Canonical\nSTATUS: open\nMODE: hitl\n")
        (modes / "02-bold.md").write_text("# Bold\nSTATUS: open\n**Mode:** afk\n")
        (modes / "03-typo.md").write_text("# Typo\nSTATUS: open\nMODE: hilt\n")

        # Plan with real fog (should stay in the ranked open list).
        foggy = self.tmp / "plans" / "foggy-plan"
        foggy.mkdir(parents=True)
        (foggy / "00-overview.md").write_text(textwrap.dedent("""
            # Foggy Plan

            ## Not yet specified

            - Open design question.

            ## Notes
            """).lstrip())

        # Plan with all concerns closed but real fog — must not vanish.
        closed_but_foggy = self.tmp / "plans" / "closed-but-foggy"
        closed_but_foggy.mkdir(parents=True)
        (closed_but_foggy / "01-a.md").write_text("# A\nSTATUS: closed\n")
        (closed_but_foggy / "00-overview.md").write_text(textwrap.dedent("""
            # Closed But Foggy

            ## Not yet specified

            - Still an open question.
            """).lstrip())

        # Plan with `- (none)` fog marker and no design-pending — should not
        # count as fog and, being all-closed, should not appear as open.
        clean = self.tmp / "plans" / "clean-plan"
        clean.mkdir(parents=True)
        (clean / "01-a.md").write_text("# A\nSTATUS: closed\n")
        (clean / "00-overview.md").write_text(textwrap.dedent("""
            # Clean Plan

            ## Not yet specified

            - (none)
            """).lstrip())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def _run(self, *extra_args):
        return subprocess.run(
            [sys.executable, str(Path(__file__).parent / "scan.py"), str(self.tmp), *extra_args],
            capture_output=True, text=True, check=True,
        )

    def test_json_typod_mode_counts_hitl_and_warns(self):
        result = self._run("--format", "json")
        data = json.loads(result.stdout)
        modes_plan = next(p for p in data["plans"] if p["name"] == "modes-plan")
        self.assertEqual(modes_plan["hitl_open"], 2)  # canonical hitl + typo'd (fail-closed)
        typo_concern = next(c for c in modes_plan["concerns"] if "typo" in c["path"])
        self.assertEqual(typo_concern["mode"], "hitl")
        self.assertEqual(len(typo_concern["warnings"]), 1)
        bold_concern = next(c for c in modes_plan["concerns"] if "bold" in c["path"])
        self.assertEqual(bold_concern["mode"], "afk")
        canonical_concern = next(c for c in modes_plan["concerns"] if "canonical" in c["path"])
        self.assertEqual(canonical_concern["mode"], "hitl")
        self.assertEqual(canonical_concern["warnings"], [])

    def test_foggy_plan_appears_in_ranked_open_list(self):
        result = self._run("--format", "summary", "--rank")
        self.assertIn("foggy-plan", result.stdout)

    def test_closed_but_foggy_plan_does_not_vanish(self):
        result = self._run("--format", "summary", "--rank")
        self.assertIn("closed-but-foggy", result.stdout)
        self.assertIn("fog present", result.stdout)

    def test_clean_plan_with_none_marker_not_open(self):
        result = self._run("--format", "summary", "--rank")
        # clean-plan is all-closed with only the canonical empty fog marker —
        # it must not appear in the open-plans table.
        for line in result.stdout.splitlines():
            self.assertNotIn("clean-plan", line)

    def test_json_totals_reflect_fog_and_hitl(self):
        result = self._run("--format", "json")
        data = json.loads(result.stdout)
        totals = data["totals"]
        self.assertGreaterEqual(totals["hitl_open_concerns"], 2)
        self.assertGreaterEqual(totals["plans_with_fog"], 2)  # foggy-plan + closed-but-foggy


class AggregationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wip-agg-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def _plan(self, name: str, concerns: list[tuple[str, str]]):
        """concerns: list of (filename, full-content) tuples."""
        d = self.tmp / "plans" / name
        d.mkdir(parents=True, exist_ok=True)
        for fn, body in concerns:
            (d / fn).write_text(textwrap.dedent(body).lstrip())
        return d

    def test_counts_by_status(self):
        self._plan("p1", [
            ("01-a.md", "# A\nSTATUS: open\n"),
            ("02-b.md", "# B\nSTATUS: closed\n"),
            ("03-c.md", "# C\nSTATUS: in-progress\n"),
            ("04-d.md", "# D\nSTATUS: blocked\n"),
            ("05-e.md", "# E\nSTATUS: cancelled\n"),
            ("00-overview.md", "# Overview\n"),  # should be skipped
        ])
        plans = scan.scan_plan_root(self.tmp / "plans", include_archive=False)
        self.assertEqual(len(plans), 1)
        p = plans[0]
        self.assertEqual(p["concern_count"], 5)
        self.assertEqual(p["open_count"], 3)  # open + in-progress + blocked
        self.assertEqual(p["closed_count"], 2)  # closed + cancelled

    def test_handles_flat_concerns(self):
        # A concern file directly under plans/ (not in a sub-dir) is valid — flat format.
        flat_dir = self.tmp / "plans"
        flat_dir.mkdir(parents=True, exist_ok=True)
        (flat_dir / "flat-concern.md").write_text("# Flat\nSTATUS: open\n")
        plans = scan.scan_plan_root(flat_dir, include_archive=False)
        flats = [p for p in plans if p["kind"] == "flat"]
        self.assertEqual(len(flats), 1)
        self.assertEqual(flats[0]["open_count"], 1)

    def test_archive_skipped_by_default(self):
        self._plan("archive/old-plan", [("01-a.md", "# Old\nSTATUS: open\n")])
        plans = scan.scan_plan_root(self.tmp / "plans", include_archive=False)
        self.assertFalse(any(p["name"] == "archive" for p in plans))

    def test_archive_included_with_flag(self):
        self._plan("archive/old-plan", [("01-a.md", "# Old\nSTATUS: open\n")])
        # scan_plan_root treats 'archive' as a plan dir when include_archive=True,
        # and recurses one level; test that the nested concern is found.
        plans = scan.scan_plan_root(self.tmp / "plans", include_archive=True)
        archive_plan = next((p for p in plans if p["name"] == "archive"), None)
        self.assertIsNotNone(archive_plan)
        self.assertEqual(archive_plan["open_count"], 1)

    def test_plane_promoted_count(self):
        self._plan("p1", [
            ("01.md", "# A\nSTATUS: open\nPLANE: DAGON-5\n"),
            ("02.md", "# B\nSTATUS: open\nPLANE: DAGON-6\n"),
            ("03.md", "# C\nSTATUS: open\n"),
        ])
        plans = scan.scan_plan_root(self.tmp / "plans", include_archive=False)
        self.assertEqual(plans[0]["promoted_to_plane"], 2)


class RankingTests(unittest.TestCase):
    def test_plans_with_open_concerns_surface_first(self):
        now = "2026-04-19T00:00:00+00:00"
        plans = [
            {"name": "clean", "open_count": 0, "closed_count": 5, "oldest_mtime": now, "promoted_to_plane": 0},
            {"name": "dirty", "open_count": 3, "closed_count": 0, "oldest_mtime": now, "promoted_to_plane": 0},
        ]
        ranked = scan.rank_plans(plans)
        self.assertEqual(ranked[0]["name"], "dirty")
        self.assertEqual(ranked[1]["name"], "clean")

    def test_oldest_first_among_open(self):
        plans = [
            {"name": "recent", "open_count": 2, "closed_count": 0, "oldest_mtime": "2026-04-18T00:00:00+00:00", "promoted_to_plane": 0},
            {"name": "stale",  "open_count": 2, "closed_count": 0, "oldest_mtime": "2026-01-01T00:00:00+00:00", "promoted_to_plane": 0},
        ]
        ranked = scan.rank_plans(plans)
        self.assertEqual(ranked[0]["name"], "stale")

    def test_more_open_before_less_open(self):
        now = "2026-04-19T00:00:00+00:00"
        plans = [
            {"name": "a", "open_count": 2, "closed_count": 0, "oldest_mtime": now, "promoted_to_plane": 0},
            {"name": "b", "open_count": 20, "closed_count": 0, "oldest_mtime": now, "promoted_to_plane": 0},
        ]
        ranked = scan.rank_plans(plans)
        self.assertEqual(ranked[0]["name"], "b")


class EndToEndJsonTests(unittest.TestCase):
    """Invoke scan.py as a subprocess and validate the JSON contract."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wip-e2e-"))
        plans = self.tmp / "plans" / "demo"
        plans.mkdir(parents=True)
        (plans / "01-a.md").write_text("# A\nSTATUS: open\nPRIORITY: p0\n")
        (plans / "02-b.md").write_text("# B\nSTATUS: closed\nPRIORITY: p1\nPLANE: DAGON-42\n")
        (plans / "00-overview.md").write_text("# Overview — should be skipped\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def test_json_shape(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "scan.py"), str(self.tmp), "--format", "json"],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(result.stdout)
        self.assertIn("scanned_at", data)
        self.assertIn("totals", data)
        self.assertIn("plans", data)

        totals = data["totals"]
        self.assertEqual(totals["plans"], 1)
        self.assertEqual(totals["open_plans"], 1)
        self.assertEqual(totals["concerns"], 2)
        self.assertEqual(totals["open_concerns"], 1)
        self.assertEqual(totals["closed_concerns"], 1)
        self.assertEqual(totals["promoted_concerns"], 1)

        plan = data["plans"][0]
        self.assertEqual(plan["name"], "demo")
        self.assertEqual(plan["kind"], "directory")
        self.assertEqual(len(plan["concerns"]), 2)

        concern_b = [c for c in plan["concerns"] if c["title"] == "B"][0]
        self.assertEqual(concern_b["plane_id"], "DAGON-42")
        self.assertEqual(concern_b["priority"], "p1")

    def test_summary_output_runs(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "scan.py"), str(self.tmp), "--format", "summary", "--rank"],
            capture_output=True, text=True, check=True,
        )
        self.assertIn("WIP under", result.stdout)
        self.assertIn("demo", result.stdout)

    def test_missing_dir_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "scan.py"), "/nonexistent/path"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
