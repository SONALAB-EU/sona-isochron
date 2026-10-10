"""What every results file records about how it was made."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYNCED_COMMIT = ROOT / ".git_commit"  # written by hpc/sync.sh into a copy that is not a git checkout (the cluster's)


def git_commit() -> str:
    """HEAD, flagged if tracked files have uncommitted changes.

    In a copy made by hpc/sync.sh, which is not a git checkout, the commit that sync.sh recorded.
    """
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, cwd=ROOT
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            capture_output=True, text=True, check=True, cwd=ROOT,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        if SYNCED_COMMIT.is_file():
            return f"{SYNCED_COMMIT.read_text(encoding='utf-8').strip()} (synced copy, recorded by hpc/sync.sh)"
        return "unknown (not a git checkout)"
    return f"{sha} (with uncommitted changes to tracked files)" if dirty else sha
