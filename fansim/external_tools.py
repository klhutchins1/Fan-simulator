"""Where optional external tools live (GPU LBM via FluidX3D). No machine-specific defaults.

Set ``FANSIM_FLUIDX3D`` to the FluidX3D checkout (default: ``../FluidX3D`` next to this repo, as
the README says) and, on Windows, ``FANSIM_MSYS_BIN`` to the msys2 runtime DLL folder FluidX3D was
built against (default ``C:\\msys64\\ucrt64\\bin``).
"""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ENV_FLUIDX3D = "FANSIM_FLUIDX3D"
ENV_MSYS_BIN = "FANSIM_MSYS_BIN"


def fluidx3d_dir() -> Path:
    raw = os.environ.get(ENV_FLUIDX3D)
    return Path(raw) if raw else REPO.parent / "FluidX3D"


def fluidx3d_exe() -> Path:
    name = "FluidX3D.exe" if os.name == "nt" else "FluidX3D"
    return fluidx3d_dir() / "bin" / name


def msys_bin() -> str:
    return os.environ.get(ENV_MSYS_BIN) or r"C:\msys64\ucrt64\bin"


def missing_fluidx3d_message() -> str:
    return (f"FluidX3D not found at {fluidx3d_exe()} — set {ENV_FLUIDX3D} to your FluidX3D "
            f"checkout (and {ENV_MSYS_BIN} to its msys2 runtime bin on Windows)")
