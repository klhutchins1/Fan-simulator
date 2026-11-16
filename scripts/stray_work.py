"""List work that exists only on this machine: uncommitted, unpushed, or on no branch.

Checks every worktree of this repo (the main checkout, `T:/Projects/fansim-*`, `.claude/worktrees/*`, the night
runner's). Anything reported here is invisible to the other agents and to GitHub until it is committed and pushed.

    python scripts/stray_work.py          # prints the list; exit 1 if anything is stray

`scripts/morning_check.py` puts the same list in `runs/night/STATUS.md` under "Work outside the repo".
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Stray:
    path: str
    branch: str | None      # None = detached HEAD
    modified: int           # tracked files with uncommitted changes
    untracked: int          # untracked files not covered by .gitignore
    unpushed: int           # commits reachable from HEAD but from no remote branch
    on_remote: bool         # the branch exists on origin

    @property
    def stray(self) -> bool:
        return bool(self.modified or self.untracked or self.unpushed)


def _git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def worktrees(repo: Path) -> list[tuple[Path, str | None]]:
    out, path = [], None
    for line in _git(repo, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = Path(line.split(" ", 1)[1].strip())
        elif line.startswith("branch ") and path:
            out.append((path, line.split(" ", 1)[1].strip().removeprefix("refs/heads/")))
            path = None
        elif line.strip() == "detached" and path:
            out.append((path, None))
            path = None
        elif line.startswith("bare"):
            path = None
    return out


def check(path: Path, branch: str | None) -> Stray:
    status = _git(path, "status", "--porcelain", "--untracked-files=all").splitlines()
    untracked = sum(1 for s in status if s.startswith("??"))
    unpushed = len(_git(path, "rev-list", "HEAD", "--not", "--remotes").split())
    on_remote = bool(branch) and bool(_git(path, "rev-parse", "--verify", "-q", f"refs/remotes/origin/{branch}"))
    return Stray(str(path), branch, len(status) - untracked, untracked, unpushed, on_remote)


def scan(repo: Path = ROOT) -> list[Stray]:
    """Every worktree of `repo` that holds work not on origin. Fetching is the caller's job."""
    found = []
    for path, branch in worktrees(repo):
        if path.is_dir():
            s = check(path, branch)
            if s.stray:
                found.append(s)
    return found


def lines(found: list[Stray]) -> list[str]:
    if not found:
        return ["- nothing: every worktree is committed and pushed."]
    out = []
    for s in found:
        what = []
        if s.modified:
            what.append(f"{s.modified} uncommitted")
        if s.untracked:
            what.append(f"{s.untracked} untracked")
        if s.unpushed:
            where = "on no branch" if s.branch is None else ("not pushed" if s.on_remote else "branch not on GitHub")
            what.append(f"{s.unpushed} commit(s) {where}")
        out.append(f"- `{s.path}` ({s.branch or 'detached'}): {', '.join(what)}. Commit and push it, "
                   f"or put it on the board as abandoned.")
    return out


def main() -> int:
    _git(ROOT, "fetch", "-q", "origin")
    found = scan(ROOT)
    print("\n".join(lines(found)))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
