"""Read last night's results, close the jobs, merge what is safely green, and write one status file.

    python scripts/morning_check.py            # write runs/night/STATUS.md only
    python scripts/morning_check.py --apply    # also update night/queue.json on master, merge, and push

The night runner calls this with ``--apply`` after its last job, so no agent has to spend a session on it.
Agents read ``runs/night/STATUS.md`` (main checkout) first; it lists what still needs a person or an agent.

Verdict per job:
- ``exit 0`` is green. A pytest job that printed "N passed" with no failures but exited non-zero is green too
  (the known OCCT/VTK teardown crash). Anything else is red. "not started" stays queued.

``--apply`` then, in a throwaway worktree of ``origin/master``:
- sets each job's ``status`` to ``done`` or ``failed`` with a note;
- merges a branch ``--no-ff`` only if **all** of these hold: one of its jobs has ``"merge_on_green": true``; every
  queue job for that branch is green or already done; the branch has not moved since the job ran; master has
  changed nothing but docs since the branch forked from it; and the merge has no conflict. Otherwise it says why
  in STATUS.md and leaves the merge to an agent;
- pushes master. It never force-pushes and never edits the board: the agent that owns the task writes its
  ``done <commit>`` line.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("pytest_chunks", Path(__file__).with_name("pytest_chunks.py"))
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)

DOC_PREFIXES = ("docs/", "night/", "handoff/")


def verdict(rec: dict, log_text: str) -> tuple[bool | None, str]:
    """(green?, one line). None = the job did not run."""
    result = str(rec.get("result", ""))
    if result.startswith("not started"):
        return None, result
    m = re.fullmatch(r"exit (-?\d+)", result)
    if not m:
        return False, result or "no result"
    rc = int(m.group(1))
    chunk_lines = [ln.strip() for ln in log_text.splitlines() if re.match(r"chunk \d+: ", ln)]
    if chunk_lines:
        ok = all(re.match(r"chunk \d+: passed", ln) for ln in chunk_lines)
        return ok, "; ".join(chunk_lines)
    if rc == 0:
        return True, "exit 0"
    summary = None
    for ln in log_text.splitlines():
        if pc._parse_summary(ln) is not None:
            summary = ln.strip().strip("=").strip()
    ok, text = pc.judge(rc, summary)
    return ok, text


def doc_only(paths: list[str]) -> bool:
    return all(p.startswith(DOC_PREFIXES) or p.endswith(".md") for p in paths)


def branches_to_merge(jobs: list[dict], green: dict[str, bool | None]) -> list[str]:
    """Branches whose every queue job is green tonight or already done, and that asked for the merge."""
    out = []
    for branch in dict.fromkeys(j["branch"] for j in jobs if j.get("branch")):
        mine = [j for j in jobs if j.get("branch") == branch]
        if not any(j.get("merge_on_green") for j in mine):
            continue
        if not any(green.get(j["id"]) is True for j in mine):
            continue
        if all(green.get(j["id"]) is True or (j["id"] not in green and j.get("status") == "done") for j in mine):
            out.append(branch)
    return out


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)


def _latest_day(night: Path) -> Path | None:
    days = sorted(d for d in night.glob("20??-??-??") if (d / "results.json").exists())
    return days[-1] if days else None


def _try_merge(wt: Path, branch: str, tested: dict[str, str]) -> tuple[str | None, str]:
    """(merge commit or None, why)."""
    head = _git(wt, "rev-parse", f"origin/{branch}", check=False).stdout.strip()
    if not head:
        return None, "branch is not on origin: push it"
    if any(sha != head for sha in tested.values()) or not tested:
        return None, "branch moved after its gate ran (or the run recorded no sha): gate again"
    base = _git(wt, "merge-base", "HEAD", head).stdout.strip()
    changed = [p for p in _git(wt, "diff", "--name-only", base, "HEAD").stdout.splitlines() if p]
    if not doc_only(changed):
        return None, "master changed code since this branch forked: merge master into the branch and gate again"
    msg = f"Merge branch '{branch}': night gate green ({head[:7]}), merged by morning_check"
    if _git(wt, "merge", "--no-ff", "-m", msg, head, check=False).returncode != 0:
        _git(wt, "merge", "--abort", check=False)
        return None, "merge conflict: an agent must merge it"
    return _git(wt, "rev-parse", "--short", "HEAD").stdout.strip(), "merged"


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="update the queue on master, merge green branches, push")
    ap.add_argument("--day", type=Path, default=None, help="a runs/night/<date> folder (default: the latest)")
    args = ap.parse_args(argv)

    root = Path(root) if root else ROOT
    try:
        main_co = Path(_git(root, "worktree", "list", "--porcelain").stdout.splitlines()[0].split(" ", 1)[1].strip())
    except (subprocess.CalledProcessError, IndexError):
        main_co = root
    night = main_co / "runs" / "night"
    day = args.day or _latest_day(night)
    if day is None:
        print("no night results found")
        return 0
    records = json.loads((day / "results.json").read_text(encoding="utf-8"))

    rows, green, shas = [], {}, {}
    for rec in records:
        try:
            log_text = Path(rec.get("log", "")).read_text(encoding="utf-8", errors="replace")
        except OSError:
            log_text = ""
        ok, text = verdict(rec, log_text)
        green[rec["id"]] = ok
        shas[rec["id"]] = rec.get("sha", "")
        rows.append((rec["id"], ok, text))

    _git(root, "fetch", "-q", "origin", check=False)
    merges: dict[str, tuple[str | None, str]] = {}
    pushed = "not applied (run with --apply)"
    queue_text = _git(root, "show", "origin/master:night/queue.json", check=False).stdout
    jobs = json.loads(queue_text).get("jobs", []) if queue_text else []

    if args.apply and not jobs:
        pushed = ("APPLY SKIPPED: could not read night/queue.json from origin/master (fetch or ssh problem?). "
                  "The jobs were not closed and nothing was merged")
    if args.apply and jobs:
        wt = night / "wt-morning"
        if wt.exists():
            _git(root, "worktree", "remove", "--force", str(wt), check=False)
        try:
            _git(root, "worktree", "add", "-q", "--detach", str(wt), "origin/master")
            for branch in branches_to_merge(jobs, green):
                tested = {j["id"]: shas.get(j["id"], "") for j in jobs
                          if j.get("branch") == branch and green.get(j["id"]) is True}
                merges[branch] = _try_merge(wt, branch, tested)
            qpath = wt / "night" / "queue.json"
            raw = qpath.read_text(encoding="utf-8")
            queue = json.loads(raw)
            touched = False
            for job in queue.get("jobs", []):
                ok = green.get(job["id"])
                if ok is None or job.get("status") not in ("queued", "rerun"):
                    continue
                text = next(t for i, _, t in rows if i == job["id"])
                job["status"] = "done" if ok else "failed"
                note = f"{day.name}: {text[:300]}"
                merged = merges.get(job.get("branch", ""), (None, ""))
                if merged[0]:
                    note += f" Merged to master {merged[0]}."
                elif merged[1]:
                    note += f" Not merged: {merged[1]}."
                job["note"] = note
                touched = True
            if touched:
                qpath.write_text(json.dumps(queue, indent=1) + ("\n" if raw.endswith("\n") else ""),
                                 encoding="utf-8", newline="")
                _git(wt, "commit", "-q", "-am", f"night: morning check {day.name} (jobs closed by morning_check)")
            if touched or any(m[0] for m in merges.values()):
                push = _git(wt, "push", "-q", "origin", "HEAD:master", check=False)
                pushed = "pushed to origin/master" if push.returncode == 0 else (
                    "PUSH FAILED (master moved?): an agent must close the jobs. " + push.stderr.strip()[:200])
            else:
                pushed = "nothing to push"
        except Exception as exc:  # noqa: BLE001  the status file must still be written
            detail = getattr(exc, "stderr", "") or str(exc)
            pushed = f"APPLY FAILED: {type(exc).__name__}: {str(detail).strip()[:240]}. The jobs were not closed"
        finally:
            _git(root, "worktree", "remove", "--force", str(wt), check=False)

    mark = {True: "green", False: "RED", None: "not run"}
    lines = [f"# Night status: {day.name}", "", f"Queue and merges: {pushed}.", "",
             "| job | result | detail |", "|---|---|---|"]
    lines += [f"| {i} | {mark[ok]} | {text[:200]} |" for i, ok, text in rows]
    if merges:
        lines += ["", "## Branches", ""]
        lines += [f"- `{b}`: {'merged ' + c if c else 'NOT merged: ' + why}" for b, (c, why) in merges.items()]
    todo = [f"- `{i}` is red: read its log in `{day}`." for i, ok, _ in rows if ok is False]
    todo += [f"- `{i}` did not start (peak window): it stays queued." for i, ok, _ in rows if ok is None]
    todo += [f"- `{b}`: {why}." for b, (c, why) in merges.items() if not c]
    by_id = {j["id"]: j for j in jobs}
    todo += [f"- `{i}` is green on `{by_id[i]['branch']}` with no `merge_on_green`: an agent merges it."
             for i, ok, _ in rows if ok and i in by_id and by_id[i].get("branch")
             and by_id[i]["branch"] not in merges and not by_id[i].get("merge_on_green")
             and by_id[i].get("status") in ("queued", "rerun")]
    if pushed.startswith("APPLY"):
        todo.insert(0, f"- {pushed}. Close the jobs in night/queue.json by hand and merge any green branch.")
    lines += ["", "## Needs an agent", "", *(todo or ["- nothing."]), ""]
    night.mkdir(parents=True, exist_ok=True)
    (night / "STATUS.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
