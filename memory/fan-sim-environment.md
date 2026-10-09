---
name: fan-sim-environment
description: Fan-simulator dev toolchain, hardware, and the Python 3.12 pin gotcha
metadata:
  type: project
---

Machine: Windows 11, **RTX 4070 Ti (12 GB)**, many CPU cores, Docker 29, WSL2 (v2.6.3),
`uv` 0.11.1, git 2.53. No conda.

**Python 3.12 pin (important):** system Python is **3.14**, which has NO wheels for the CAD
kernel (CadQuery/OCP/OpenCASCADE). The project pins `requires-python = ">=3.12,<3.13"` and
`uv` auto-fetches 3.12. Verified working: CadQuery 2.8.0 + OCP on Python 3.12.5, trimesh
5.0, numpy 2.5. Always run via `uv run` (not the system `python`).

Commands:
- `uv sync` (core geometry) / `uv sync --extra viz` (pyvista/trame) / `--extra dev` (pytest).
- Tests: `uv run --extra dev pytest -q`. On this machine prefix `UV_LINK_MODE=copy` to avoid
  a hardlink warning (cache and project on different filesystems: C: vs E:).
- Project lives on `E:\Projects\programming_2\Fan-simulator`; uv cache on `C:`.

CFD engines are external binaries, NOT pip deps: OpenFOAM (Docker) + FluidX3D (GPU).

pytest needs `pythonpath = ["."]` in pyproject (set) so `fansim` imports without install.

See [[fan-sim-project]] for scope and [[fan-sim-status]] for progress.
