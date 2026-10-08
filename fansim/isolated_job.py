"""Shared JSON-job subprocess runner for CadQuery/CFD workers.

Build/eval callers write a temp job file and run ``python -m <module> <job.json>``.
A crash or hang in OCP/OpenFOAM stays in the child process.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from fansim.optimize.objectives import ObjectiveResult

# A CFD worker is killed when its case directory shows no new output for this long. Streamed
# OpenFOAM logs grow every iteration and snappy prints throughout meshing, so 15 min of silence
# means hung, not slow. A slow-but-progressing run (e.g. the desktop is busy) keeps going.
DEFAULT_STALL_TIMEOUT_S = 900.0
ENV_STALL_TIMEOUT = "FANSIM_CFD_STALL_TIMEOUT"


def stall_timeout(override: float | None = None) -> float:
    """Resolve the no-progress window: explicit override > env > default."""
    if override is not None:
        return float(override)
    raw = os.environ.get(ENV_STALL_TIMEOUT)
    if raw not in (None, ""):
        try:
            return max(60.0, float(raw))
        except ValueError:
            pass
    return DEFAULT_STALL_TIMEOUT_S


def latest_activity(watch_dir: Path) -> float:
    """Newest mtime among the case's progress files (top-level, logs/, postProcessing/*/*/)."""
    newest = 0.0
    dirs = [watch_dir, watch_dir / "logs"]
    pp = watch_dir / "postProcessing"
    if pp.is_dir():
        dirs += [t for fo in pp.iterdir() if fo.is_dir() for t in fo.iterdir() if t.is_dir()]
    for d in dirs:
        try:
            with os.scandir(d) as it:
                for e in it:
                    if e.is_file():
                        newest = max(newest, e.stat().st_mtime)
        except OSError:
            continue
    return newest


def watch_process(
    proc,
    *,
    watch_dir: Path | None,
    hard_timeout_s: float,
    stall_s: float,
    poll_s: float = 5.0,
    clock: Callable[[], float] = time.time,
    sleep: Callable[[float], None] = time.sleep,
) -> str | None:
    """Wait for ``proc``; return ``None`` when it exits, or why it should be killed.

    Returns ``"stall"`` when ``watch_dir`` has had no new output for ``stall_s`` (only checked
    when ``watch_dir`` is given), or ``"timeout"`` past ``hard_timeout_s``. The caller kills.
    """
    t0 = clock()
    last = t0
    while proc.poll() is None:
        now = clock()
        if now - t0 > hard_timeout_s:
            return "timeout"
        if watch_dir is not None:
            last = max(last, latest_activity(Path(watch_dir)))
            if now - last > stall_s:
                return "stall"
        sleep(poll_s)
    return None


def run_worker_module(
    module: str,
    job: dict,
    *,
    timeout: float,
    label: str,
    require_paths: Sequence[Path] | None = None,
    stderr_tail: int = 160,
    watch_dir: Path | str | None = None,
    stall_s: float | None = None,
) -> subprocess.CompletedProcess:
    """Run ``python -m module <job.json>``; delete the job file afterward.

    Raises ``TimeoutError`` if the worker exceeds ``timeout``, or ``RuntimeError`` if
    the exit code is non-zero or any ``require_paths`` is missing. With ``watch_dir`` (a CFD
    case dir), ``timeout`` is a hard cap and the worker is also killed after ``stall_s``
    (default :func:`stall_timeout`) without new output there.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as jf:
        json.dump(job, jf)
        jobfile = jf.name
    try:
        if watch_dir is not None:
            returncode, stdout, stderr = run_watched(
                [sys.executable, "-m", module, jobfile],
                watch_dir=Path(watch_dir), hard_timeout_s=timeout,
                stall_s=stall_timeout(stall_s), label=label,
            )
            proc = subprocess.CompletedProcess([module, jobfile], returncode, stdout, stderr)
        else:
            try:
                proc = subprocess.run(
                    [sys.executable, "-m", module, jobfile],
                    capture_output=True, text=True, timeout=timeout,
                )
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError(f"{label} exceeded {timeout:.0f}s") from exc
    finally:
        Path(jobfile).unlink(missing_ok=True)

    missing = [p for p in (require_paths or ()) if not Path(p).exists()]
    if proc.returncode != 0 or missing:
        tail = (proc.stderr or "").strip()[-stderr_tail:] or "native crash"
        raise RuntimeError(f"{label} failed (exit {proc.returncode}): {tail}")
    return proc


def terminate_worker(proc: subprocess.Popen) -> None:
    """Kill an eval worker and its children (Windows needs taskkill /T for the Docker tree)."""
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True, text=True,
        )
    else:
        proc.kill()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def run_watched(
    cmd: list[str],
    *,
    watch_dir: Path,
    hard_timeout_s: float,
    stall_s: float,
    label: str,
    proc_holder: list | None = None,
) -> tuple[int, str, str]:
    """Run a CFD worker under :func:`watch_process`; return ``(returncode, stdout, stderr)``.

    Worker output goes to ``watch_dir/_worker.{out,err}`` (files, not pipes, so a chatty worker
    can't deadlock the poll loop). On stall/timeout the worker tree and its OpenFOAM containers
    are killed and ``TimeoutError`` is raised. ``proc_holder`` (one-slot list) receives the live
    ``Popen`` so a Cancel button can terminate it.
    """
    watch_dir.mkdir(parents=True, exist_ok=True)
    out_path, err_path = watch_dir / "_worker.out", watch_dir / "_worker.err"
    with open(out_path, "w", encoding="utf-8") as out, open(err_path, "w", encoding="utf-8") as err:
        proc = subprocess.Popen(cmd, stdout=out, stderr=err, text=True)
        if proc_holder is not None:
            if proc_holder:
                proc_holder[0] = proc
            else:
                proc_holder.append(proc)
        try:
            why = watch_process(
                proc, watch_dir=watch_dir, hard_timeout_s=hard_timeout_s, stall_s=stall_s)
            if why is not None:
                terminate_worker(proc)
                try:
                    from fansim.cfd.runner import kill_cfd_containers
                    kill_cfd_containers()
                except Exception:  # noqa: BLE001 — cleanup must not mask the timeout
                    pass
                if why == "stall":
                    raise TimeoutError(
                        f"{label} stalled: no CFD progress for {stall_s / 60:.0f} min "
                        f"(set {ENV_STALL_TIMEOUT}=SECONDS to change)")
                raise TimeoutError(f"{label} exceeded the {hard_timeout_s / 60:.0f} min hard cap")
        finally:
            if proc_holder is not None and proc_holder and proc_holder[0] is proc:
                proc_holder[0] = None
    read = lambda p: p.read_text(encoding="utf-8", errors="replace")  # noqa: E731
    return proc.returncode, read(out_path), read(err_path)


def load_objective_result(path: Path | str) -> ObjectiveResult:
    """Load an ``ObjectiveResult`` written by an eval worker."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return ObjectiveResult(**data)
