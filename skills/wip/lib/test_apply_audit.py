#!/usr/bin/env python3
"""
test_apply_audit.py — stdlib unittest suite for apply_audit.py.

Covers the STATUS-rewrite engine: canonical vs bold-markdown formats, no-ops,
resolution appending, sync-trail comments, and safety guards (status-mismatch
protection, confidence filtering).

Run:
  python3 ~/.claude/skills/wip/lib/test_apply_audit.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import apply_audit  # noqa: E402


class RewriteStatusTests(unittest.TestCase):
    def test_canonical_open_to_done(self):
        text = "# T\nSTATUS: open\nPRIORITY: p0\n"
        new, changed, fmt = apply_audit.rewrite_status(text, "done", "open")
        self.assertTrue(changed)
        self.assertEqual(fmt, "canonical")
        self.assertIn("STATUS: done", new)
        self.assertNotIn("STATUS: open", new)

    def test_bold_open_to_closed_preserves_period(self):
        text = "# T\n**Status:** open.\n"
        new, changed, fmt = apply_audit.rewrite_status(text, "closed", "open")
        self.assertTrue(changed)
        self.assertEqual(fmt, "bold")
        self.assertIn("**Status:** closed.", new)

    def test_mismatch_refuses_to_write(self):
        text = "# T\nSTATUS: in-progress\n"
        new, changed, fmt = apply_audit.rewrite_status(text, "done", "open")
        self.assertFalse(changed)
        self.assertEqual(fmt, "mismatch")
        self.assertEqual(new, text)

    def test_missing_status_returns_none(self):
        text = "# T\nNo status here.\n"
        new, changed, fmt = apply_audit.rewrite_status(text, "done", "open")
        self.assertFalse(changed)
        self.assertEqual(fmt, "none")

    def test_canonical_takes_precedence_over_bold(self):
        text = "# T\nSTATUS: open\n**Status:** something\n"
        new, changed, fmt = apply_audit.rewrite_status(text, "done", "open")
        self.assertTrue(changed)
        self.assertEqual(fmt, "canonical")
        # The bold line should NOT have changed.
        self.assertIn("**Status:** something", new)


class AppendResolutionTests(unittest.TestCase):
    def test_appends_new_section_when_absent(self):
        text = "# T\nSTATUS: done\n\nsome body\n"
        new = apply_audit.append_resolution(text, "Shipped in X", "commit abc123")
        self.assertIn("## Resolution", new)
        self.assertIn("Shipped in X", new)
        self.assertIn("Evidence: commit abc123", new)

    def test_appends_bullet_to_existing_section(self):
        text = "# T\nSTATUS: done\n\n## Resolution\n\n- older note\n"
        new = apply_audit.append_resolution(text, "Another closure", "commit def456")
        # Existing section preserved + new bullet added.
        self.assertIn("older note", new)
        self.assertIn("Another closure", new)

    def test_inserts_before_sync_trail(self):
        text = "# T\nSTATUS: open\n\nbody\n\n<!-- sync-plans: STATUS open -> closed -->\n"
        new = apply_audit.append_resolution(text, "R", "E")
        # Resolution section should sit *before* the sync-trail comment.
        res_idx = new.find("## Resolution")
        sync_idx = new.find("<!-- sync-plans:")
        self.assertLess(res_idx, sync_idx)
        self.assertGreater(res_idx, 0)


class SyncTrailTests(unittest.TestCase):
    def test_appends_trail_comment(self):
        text = "# T\nSTATUS: done\nbody\n"
        new = apply_audit.append_sync_trail(text, "open", "done", "commit abc123")
        self.assertIn("<!-- wip-triage: STATUS open → done", new)
        self.assertIn("commit abc123", new)

    def test_trail_handles_missing_final_newline(self):
        text = "# T\nSTATUS: done\nbody"  # no trailing newline
        new = apply_audit.append_sync_trail(text, "open", "done", "ev")
        self.assertTrue(new.endswith("-->\n") or new.endswith("-->"))


class ApplyItemTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="apply-audit-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def _write_concern(self, rel: str, body: str) -> Path:
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(body).lstrip())
        return p

    def _item(self, path, current, recommended, confidence="high", evidence="E", resolution="R"):
        return {
            "path": str(path),
            "current_status": current,
            "recommended_status": recommended,
            "confidence": confidence,
            "evidence": evidence,
            "resolution": resolution,
        }

    def test_applies_canonical_open_to_done(self):
        p = self._write_concern("plans/x/01.md", """
            # Something
            STATUS: open
            """)
        r = apply_audit.apply_item(self._item(p, "open", "done"), self.tmp, dry_run=False)
        self.assertEqual(r["action"], "wrote")
        text = p.read_text()
        self.assertIn("STATUS: done", text)
        self.assertIn("## Resolution", text)
        self.assertIn("<!-- wip-triage:", text)

    def test_dry_run_does_not_write(self):
        p = self._write_concern("plans/x/01.md", """
            # Something
            STATUS: open
            """)
        original = p.read_text()
        r = apply_audit.apply_item(self._item(p, "open", "done"), self.tmp, dry_run=True)
        self.assertEqual(r["action"], "would-write")
        self.assertEqual(p.read_text(), original)

    def test_noop_when_current_matches_recommended(self):
        p = self._write_concern("plans/x/01.md", """
            # Something
            STATUS: done
            """)
        r = apply_audit.apply_item(self._item(p, "done", "done"), self.tmp, dry_run=False)
        self.assertEqual(r["action"], "skip")
        self.assertEqual(r["reason"], "noop")

    def test_refuses_when_file_status_mismatches(self):
        # audit says current=open; file actually says closed.
        p = self._write_concern("plans/x/01.md", """
            # Something
            STATUS: closed
            """)
        r = apply_audit.apply_item(self._item(p, "open", "done"), self.tmp, dry_run=False)
        self.assertEqual(r["action"], "skip")
        self.assertIn("status-mismatch", r["reason"])
        # File should be untouched.
        self.assertIn("STATUS: closed", p.read_text())

    def test_missing_file_reports_gracefully(self):
        item = self._item(self.tmp / "plans/x/nonexistent.md", "open", "done")
        r = apply_audit.apply_item(item, self.tmp, dry_run=False)
        self.assertEqual(r["action"], "skip")
        self.assertEqual(r["reason"], "file-missing")

    def test_bold_format_round_trip(self):
        p = self._write_concern("plans/x/01.md", """
            # Something
            **Status:** open.
            """)
        r = apply_audit.apply_item(self._item(p, "open", "closed"), self.tmp, dry_run=False)
        self.assertEqual(r["action"], "wrote")
        text = p.read_text()
        self.assertIn("**Status:** closed.", text)


class CLITests(unittest.TestCase):
    """End-to-end via subprocess."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="apply-audit-cli-"))
        plans_a = self.tmp / "plans" / "a"
        plans_a.mkdir(parents=True)
        (plans_a / "01.md").write_text("# A\nSTATUS: open\nPRIORITY: p0\n")
        (plans_a / "02.md").write_text("# B\nSTATUS: open\n")
        self.audit = [
            {"path": "plans/a/01.md", "current_status": "open", "recommended_status": "done",
             "confidence": "high", "evidence": "commit xyz", "resolution": "Shipped."},
            {"path": "plans/a/02.md", "current_status": "open", "recommended_status": "done",
             "confidence": "low", "evidence": "uncertain", "resolution": None},
        ]
        self.audit_path = self.tmp / "audit.json"
        self.audit_path.write_text(json.dumps(self.audit))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(Path(__file__).parent / "apply_audit.py"),
             str(self.audit_path), "--repo", str(self.tmp), *args],
            capture_output=True, text=True, check=True,
        )

    def test_confidence_high_only_writes_high(self):
        self._run("--confidence", "high")
        self.assertIn("STATUS: done", (self.tmp / "plans/a/01.md").read_text())
        self.assertIn("STATUS: open", (self.tmp / "plans/a/02.md").read_text())  # low confidence, skipped

    def test_confidence_high_low_writes_both(self):
        self._run("--confidence", "high,low")
        self.assertIn("STATUS: done", (self.tmp / "plans/a/01.md").read_text())
        self.assertIn("STATUS: done", (self.tmp / "plans/a/02.md").read_text())

    def test_dry_run_writes_nothing(self):
        self._run("--confidence", "high", "--dry-run")
        self.assertIn("STATUS: open", (self.tmp / "plans/a/01.md").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
