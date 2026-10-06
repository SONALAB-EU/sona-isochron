"""What every results file records about how it was made."""

from __future__ import annotations

import subprocess


def git_commit() -> str:
    """HEAD, flagged if tracked files have uncommitted changes."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown (not a git checkout)"
    return f"{sha} (with uncommitted changes to tracked files)" if dirty else sha
