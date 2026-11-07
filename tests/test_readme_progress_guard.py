"""Regression tests for the README progress PR gate (standard library only)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_readme_progress import ProgressError, progress_body, validate_progress

BASE = """# Scalar Wave Viz

## Project progress — verified November 1, 2026

**2 of 5** gates accepted.
- **P2 — DRAFT:** R8 pending.

## How you can support the project

Contribute.
"""
UPDATED = BASE.replace("R8 pending.", "R9 changes required; R10 remediation next.")


class ReadmeProgressGuardTests(unittest.TestCase):
    def assert_denied(self, base, head, changed):
        with self.assertRaises(ProgressError):
            validate_progress(base, head, changed)

    def test_requires_readme_for_application_code(self):
        self.assert_denied(BASE, BASE, ["explorer/explorer.js"])

    def test_requires_readme_for_science_tests_and_docs(self):
        for path in ["electrostatics_numerics.py", "tests/test_solver.py",
                     "docs/ROADMAP.md", "assets/research-progress.svg",
                     ".github/workflows/physics-tests.yml"]:
            with self.subTest(path=path):
                self.assert_denied(BASE, BASE, [path])

    def test_other_readme_section_does_not_count(self):
        self.assert_denied(BASE, BASE.replace("Contribute.", "Please contribute."),
                           ["README.md", "explorer/explorer.js"])

    def test_date_only_change_does_not_count(self):
        self.assert_denied(BASE, BASE.replace("November 1", "November 7"),
                           ["README.md", "explorer/explorer.js"])

    def test_whitespace_only_change_does_not_count(self):
        self.assert_denied(BASE, BASE.replace("**2 of 5**", " **2   of   5** "),
                           ["README.md", "explorer/explorer.js"])

    def test_meaningful_progress_update_passes(self):
        result = validate_progress(BASE, UPDATED, ["README.md", "explorer/explorer.js"])
        self.assertIn("changed", result)

    def test_stacked_branch_behavior_is_base_relative(self):
        # validate_progress consumes merge-base/head blobs, not README from main.
        stacked_base = UPDATED
        stacked_head = UPDATED.replace("R10 remediation next.", "R10 verified by CI.")
        self.assertIn(
            "changed",
            validate_progress(stacked_base, stacked_head,
                              ["README.md", "explorer/explorer.css"]),
        )
        self.assert_denied(stacked_base, stacked_base,
                           ["README.md", "explorer/explorer.css"])

    def test_readme_only_edit_is_allowed(self):
        result = validate_progress(
            BASE, BASE.replace("Contribute.", "Everyone can contribute."), ["README.md"]
        )
        self.assertIn("README-only", result)

    def test_removed_progress_section_is_rejected(self):
        self.assert_denied(BASE, "# Scalar Wave Viz\n\n## How you can support\nHi.",
                           ["README.md", "explorer/explorer.js"])
        self.assert_denied(BASE, "# Scalar Wave Viz\n\n## How you can support\nHi.",
                           ["README.md"])

    def test_noop_is_allowed(self):
        self.assertIn("No repository changes", validate_progress(BASE, BASE, []))

    def test_empty_progress_is_rejected(self):
        head = BASE.replace("**2 of 5** gates accepted.\n- **P2 — DRAFT:** R8 pending.", "")
        self.assert_denied(BASE, head, ["README.md", "explorer/explorer.js"])

    def test_progress_heading_date_not_in_normalized_body(self):
        self.assertEqual(progress_body(BASE), progress_body(
            BASE.replace("November 1, 2026", "November 7, 2026")))


if __name__ == "__main__":
    unittest.main()
