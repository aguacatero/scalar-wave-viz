#!/usr/bin/env python3
"""Fail substantive PRs without a changed README Project progress narrative.

The comparison is against the PR merge base, so stacked PRs are checked against
their actual target branch rather than against main.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

HEADING = re.compile(r"^##[ \t]+Project progress(?:[ \t]*[—–-].*)?[ \t]*$", re.I)
NEXT_HEADING = re.compile(r"^##[ \t]+")
README = "README.md"


class ProgressError(Exception):
    """README progress report is missing or has not been updated."""


def progress_body(markdown: str) -> str | None:
    """Return normalized progress content, excluding the verification-date heading."""
    lines = markdown.splitlines()
    start = next((i for i, line in enumerate(lines) if HEADING.match(line)), None)
    if start is None:
        return None
    end = next(
        (i for i in range(start + 1, len(lines)) if NEXT_HEADING.match(lines[i])),
        len(lines),
    )
    body = " ".join(line.strip() for line in lines[start + 1:end])
    return re.sub(r"\s+", " ", body).strip()


def validate_progress(base_readme: str, head_readme: str, changed_paths: list[str]) -> str:
    """Validate a PR using its merge-base/head README blobs and changed paths."""
    changed = set(changed_paths)
    if not changed:
        return "No repository changes; no progress update required."

    before = progress_body(base_readme)
    after = progress_body(head_readme)
    if before is None or after is None or not after:
        raise ProgressError("README.md must retain a nonempty '## Project progress' section.")

    # A README-only wording/onboarding change is not a separate implementation
    # milestone. Every other PR, including docs, tests, assets and CI, is gated.
    if changed == {README}:
        return "README-only PR; the project progress section is preserved."

    if README not in changed:
        raise ProgressError(
            "This PR changes files other than README.md. Update README.md's "
            "'## Project progress' narrative in the SAME PR."
        )
    if before == after:
        raise ProgressError(
            "README.md changed, but its '## Project progress' narrative did not. "
            "Changing only the heading date, formatting, or other README sections "
            "does not satisfy this check."
        )
    return "The Project progress narrative changed alongside substantive repository files."


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    )
    return result.stdout


def check_pr(base_ref: str, head_sha: str) -> str:
    # Avoid comparing with main for stacked PRs; use the true PR merge base.
    merge_base = git("merge-base", "refs/remotes/origin/" + base_ref, head_sha).strip()
    changed = [
        name for name in git(
            "diff", "--name-only", "-z", "--diff-filter=ACDMRT", merge_base, head_sha
        ).split("\0") if name
    ]
    base_readme = git("show", merge_base + ":" + README)
    head_readme = git("show", head_sha + ":" + README)
    result = validate_progress(base_readme, head_readme, changed)
    return f"{result}\nCompared merge-base {merge_base[:12]} to {head_sha[:12]} ({len(changed)} paths)."


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--head-sha", required=True)
    args = parser.parse_args()
    try:
        print("PASS: " + check_pr(args.base_ref, args.head_sha))
        return 0
    except (ProgressError, subprocess.CalledProcessError) as exc:
        print("FAIL: README progress maintenance is required.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
