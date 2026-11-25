"""Run OpenFOAM utilities inside the ESI Docker image against a local case directory.

Uses ``docker`` via subprocess (not the shell) so Windows paths are passed straight to
Docker Desktop without MSYS path mangling.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_IMAGE = "opencfd/openfoam-default:2406"


def _label_args() -> list[str]:
    """Docker --label flags so CFD containers can be found + reaped later.

    Always tags ``fansim_cfd=1`` (a generic 'this is one of ours' marker), and, when the launcher
    set ``FANSIM_CFD_SESSION`` in the environment (the cockpit --reload supervisor does), also tags
    ``fansim_cfd_session=<id>``. The env var is inherited by every subprocess, so a container started
    deep inside an isolated eval worker still carries the session's label — which lets the supervisor
    ``docker kill`` exactly its own children's containers on restart instead of orphaning them."""
    args = ["--label", "fansim_cfd=1"]
    sess = os.environ.get("FANSIM_CFD_SESSION")
    if sess:
        args += ["--label", f"fansim_cfd_session={sess}"]
    return args


def log_name(foam_command: str) -> str:
    """Log basename for a command: the OpenFOAM app, not the ``mpirun`` launcher.

    ``mpirun ... -np 8 simpleFoam -parallel`` -> ``simpleFoam`` (it used to be ``mpirun``, so
    potentialFoam's log was overwritten by simpleFoam's and neither was identifiable).
    """
    tokens = foam_command.split()
    if tokens and tokens[0] == "mpirun":
        rest = tokens[1:]
        i = 0
        while i < len(rest):
            tok = rest[i]
            if tok in ("-np", "-n", "--np", "--bind-to", "--map-by", "-x", "--mca"):
                i += 3 if tok == "--mca" else 2
            elif tok.startswith("-"):
                i += 1
            else:
                return tok.replace("/", "_")
    return tokens[0].replace("/", "_") if tokens else "command"


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass
class OpenFOAMRunner:
    """Executes OpenFOAM commands in a container with the case bind-mounted at /case."""

    case_dir: Path
    image: str = DEFAULT_IMAGE
    log_dir: Path | None = field(default=None)

    def __post_init__(self):
        self.case_dir = Path(self.case_dir).resolve()
        self.log_dir = Path(self.log_dir) if self.log_dir else self.case_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def run(self, foam_command: str, check: bool = True) -> CommandResult:
        """Run one OpenFOAM command (sourced env) in the container, logging output.

        stdout streams to ``logs/<name>.log`` WHILE the command runs (not only on exit), so a
        killed or timed-out solve still leaves its iteration history on disk, and the parent's
        stall watchdog (``fansim.isolated_job.watch_process``) sees progress as the log grows.
        """
        mount = f"{self.case_dir}:/case"
        full = (
            "source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; "
            f"cd /case && {foam_command}"
        )
        log_path = self.log_dir / f"{log_name(foam_command)}.log"
        err_path = log_path.with_suffix(".stderr.tmp")
        with open(log_path, "w", encoding="utf-8") as out, open(err_path, "w", encoding="utf-8") as err:
            proc = subprocess.run(
                ["docker", "run", "--rm", *_label_args(), "-v", mount, "-w", "/case", self.image,
                 "bash", "-lc", full],
                stdout=out, stderr=err, text=True,
            )
        stderr = err_path.read_text(encoding="utf-8", errors="replace")
        err_path.unlink(missing_ok=True)
        with open(log_path, "a", encoding="utf-8") as out:
            out.write("\n===STDERR===\n" + stderr)
        stdout = log_path.read_text(encoding="utf-8", errors="replace").split("\n===STDERR===\n")[0]
        result = CommandResult(foam_command, proc.returncode, stdout, stderr)
        if check and not result.ok:
            tail = "\n".join(stdout.splitlines()[-25:])
            raise RuntimeError(
                f"OpenFOAM command failed ({proc.returncode}): {foam_command}\n{tail}\n"
                f"{stderr[-1000:]}"
            )
        return result


def _docker_image_query(image: str) -> list[str]:
    """Argv shared by ``image_available`` and the cockpit readiness line."""
    return ["docker", "images", "-q", image]


def image_available(image: str = DEFAULT_IMAGE) -> bool:
    proc = subprocess.run(
        _docker_image_query(image), capture_output=True, text=True
    )
    return proc.returncode == 0 and bool(proc.stdout.strip())


# One sentence each. Simple mode: a hobbyist can act without knowing OpenFOAM.
_LINE_READY = "Airflow check ready. You can press Assess."
_LINE_NOT_RUNNING = (
    "Docker not running. Start Docker Desktop, wait until it is running, then press Assess."
)


@dataclass(frozen=True)
class CfdReadiness:
    """Docker/OpenFOAM state for the cockpit badge. ``line`` is the whole message."""

    state: str
    line: str


def _line_image_missing(image: str) -> str:
    return f"image missing. Pull it once: docker pull {image}"


def _line_not_installed(image: str) -> str:
    return f"Docker not installed. Install Docker Desktop, then pull {image}."


def cfd_readiness(
    image: str = DEFAULT_IMAGE, *, run=None, timeout: float = 5.0
) -> CfdReadiness:
    """Say whether Assess can run, and the one fix when it cannot.

    Uses the same ``docker images -q`` query as ``image_available``. ``docker info``
    tells "Docker not running" apart from a missing image. A missing ``docker``
    program is "Docker not installed" (``image_available`` still raises there).
    """
    run = run or subprocess.run
    try:
        info = run(["docker", "info"], capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return CfdReadiness("docker_not_installed", _line_not_installed(image))
    except (OSError, subprocess.TimeoutExpired):
        return CfdReadiness("docker_not_running", _LINE_NOT_RUNNING)
    if getattr(info, "returncode", 1) != 0:
        return CfdReadiness("docker_not_running", _LINE_NOT_RUNNING)
    try:
        images = run(
            _docker_image_query(image), capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        return CfdReadiness("docker_not_installed", _line_not_installed(image))
    except (OSError, subprocess.TimeoutExpired):
        return CfdReadiness("docker_not_running", _LINE_NOT_RUNNING)
    if getattr(images, "returncode", 1) != 0:
        return CfdReadiness("docker_not_running", _LINE_NOT_RUNNING)
    if not (getattr(images, "stdout", "") or "").strip():
        return CfdReadiness("image_missing", _line_image_missing(image))
    return CfdReadiness("ready", _LINE_READY)


def publish_cfd_readiness(state) -> str:
    """Write the one readiness line onto cockpit state. Never raises."""
    try:
        line = cfd_readiness().line
    except Exception:  # noqa: BLE001 — the cockpit still opens if the probe misbehaves
        line = _LINE_NOT_RUNNING
    state.cfd_readiness = line
    return line


def kill_cfd_containers(*, session: str | None = None, timeout: float = 30.0) -> int:
    """``docker kill`` OpenFOAM containers tagged by ``_label_args`` (best-effort).

    When ``session`` is set (or ``FANSIM_CFD_SESSION`` is in the environment), only that
    session's containers are killed; otherwise every ``fansim_cfd=1`` container that does NOT
    belong to some session is reaped (background jobs set their own session to stay safe).
    Returns how many container IDs were passed to ``docker kill``.
    """
    sess = session if session is not None else os.environ.get("FANSIM_CFD_SESSION")
    filt = f"label=fansim_cfd_session={sess}" if sess else "label=fansim_cfd=1"
    try:
        out = subprocess.run(
            ["docker", "ps", "--filter", filt, "--format",
             '{{.ID}} {{.Label "fansim_cfd_session"}}'],
            capture_output=True, text=True, timeout=min(20.0, timeout),
        )
        rows = [ln.split() for ln in out.stdout.splitlines() if ln.strip()]
        # Unscoped cleanup (a cockpit with no session) must not kill containers another
        # session owns, e.g. an overnight audit (2026-10-07: a cockpit restart killed one).
        ids = [r[0] for r in rows if sess or len(r) == 1]
        if not ids:
            return 0
        subprocess.run(
            ["docker", "kill", *ids], capture_output=True, text=True, timeout=timeout,
        )
        return len(ids)
    except Exception:  # noqa: BLE001 — cancel/timeout cleanup must not raise
        return 0
