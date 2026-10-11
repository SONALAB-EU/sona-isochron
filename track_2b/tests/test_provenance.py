"""The commit recorded in results files, in a git checkout and in a copy made by hpc/sync.sh."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from isochron import provenance


def test_git_commit_here() -> None:
    """A git checkout (the Mac) or a copy made by hpc/sync.sh (the cluster): either way a full hash."""
    assert re.match(r"[0-9a-f]{40}( \(with uncommitted changes( to tracked files)?\))?"
                    r"( \(synced copy, recorded by hpc/sync\.sh\))?$", provenance.git_commit())


def test_git_commit_in_a_synced_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_checkout(*args, **kwargs):
        raise subprocess.CalledProcessError(128, args[0])

    monkeypatch.setattr(provenance.subprocess, "run", no_checkout)
    monkeypatch.setattr(provenance, "SYNCED_COMMIT", tmp_path / ".git_commit")
    assert provenance.git_commit() == "unknown (not a git checkout)"
    (tmp_path / ".git_commit").write_text("0123456789abcdef0123456789abcdef01234567\n", encoding="utf-8")
    assert provenance.git_commit() == "0123456789abcdef0123456789abcdef01234567 (synced copy, recorded by hpc/sync.sh)"
