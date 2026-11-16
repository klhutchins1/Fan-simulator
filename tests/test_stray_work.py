"""scripts/stray_work.py: find work that lives only on this machine (uncommitted, unpushed, or on no branch)."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
_spec = importlib.util.spec_from_file_location("stray_work", SCRIPTS / "stray_work.py")
sw = importlib.util.module_from_spec(_spec)
sys.modules["stray_work"] = sw   # dataclasses look their module up here
_spec.loader.exec_module(sw)


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A bare origin and a main checkout on master with one pushed commit."""
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "master", str(origin))
    main = tmp_path / "main"
    _git(tmp_path, "clone", "-q", str(origin), str(main))
    _git(main, "config", "user.email", "t@example.com")
    _git(main, "config", "user.name", "t")
    (main / ".gitignore").write_text("runs/\n")
    (main / "a.txt").write_text("a\n")
    _git(main, "add", "-A")
    _git(main, "commit", "-q", "-m", "base")
    _git(main, "push", "-q", "origin", "HEAD:master")
    return main


def _by_path(found):
    return {Path(s.path).name: s for s in found}


def test_clean_pushed_checkout_is_not_reported(repo):
    assert sw.scan(repo) == []


def test_uncommitted_and_untracked_files_are_reported(repo):
    (repo / "a.txt").write_text("changed\n")
    (repo / "new.md").write_text("x\n")
    (repo / "runs").mkdir()
    (repo / "runs" / "ignored.json").write_text("{}")   # gitignored: not stray
    s = _by_path(sw.scan(repo))["main"]
    assert s.modified == 1 and s.untracked == 1 and s.unpushed == 0


def test_worktree_with_unpushed_commits_is_reported(repo, tmp_path):
    wt = tmp_path / "wt-feat"
    _git(repo, "worktree", "add", "-q", "-b", "feat", str(wt))
    (wt / "f.py").write_text("x = 1\n")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-q", "-m", "feat")
    s = _by_path(sw.scan(repo))["wt-feat"]
    assert s.branch == "feat" and s.unpushed == 1 and not s.on_remote


def test_pushed_worktree_is_not_reported(repo, tmp_path):
    wt = tmp_path / "wt-feat"
    _git(repo, "worktree", "add", "-q", "-b", "feat", str(wt))
    (wt / "f.py").write_text("x = 1\n")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-q", "-m", "feat")
    _git(wt, "push", "-q", "origin", "feat")
    assert sw.scan(repo) == []


def test_detached_commit_on_no_branch_is_reported(repo, tmp_path):
    wt = tmp_path / "wt-det"
    _git(repo, "worktree", "add", "-q", "--detach", str(wt))
    (wt / "d.py").write_text("y = 2\n")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-q", "-m", "loose")
    s = _by_path(sw.scan(repo))["wt-det"]
    assert s.branch is None and s.unpushed == 1


def test_lines_name_each_problem_in_plain_words(repo):
    (repo / "new.md").write_text("x\n")
    text = "\n".join(sw.lines(sw.scan(repo)))
    assert "main" in text and "1 untracked" in text
    assert sw.lines([]) == ["- nothing: every worktree is committed and pushed."]
