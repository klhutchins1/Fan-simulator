# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
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
        """Run one OpenFOAM command (sourced env) in the container, logging output."""
        mount = f"{self.case_dir}:/case"
        full = (
            "source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; "
            f"cd /case && {foam_command}"
        )
        proc = subprocess.run(
            ["docker", "run", "--rm", *_label_args(), "-v", mount, "-w", "/case", self.image,
             "bash", "-lc", full],
            capture_output=True, text=True,
        )
        name = foam_command.split()[0].replace("/", "_")
        (self.log_dir / f"{name}.log").write_text(
            proc.stdout + "\n===STDERR===\n" + proc.stderr, encoding="utf-8"
        )
        result = CommandResult(foam_command, proc.returncode, proc.stdout, proc.stderr)
        if check and not result.ok:
            tail = "\n".join(proc.stdout.splitlines()[-25:])
            raise RuntimeError(
                f"OpenFOAM command failed ({proc.returncode}): {foam_command}\n{tail}\n"
                f"{proc.stderr[-1000:]}"
            )
        return result


def image_available(image: str = DEFAULT_IMAGE) -> bool:
    proc = subprocess.run(
        ["docker", "images", "-q", image], capture_output=True, text=True
    )
    return proc.returncode == 0 and bool(proc.stdout.strip())
