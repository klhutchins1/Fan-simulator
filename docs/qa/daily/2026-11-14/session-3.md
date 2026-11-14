# 2026-11-14 session 3 — clean-clone fast suite

Write this session into `docs/qa/rounds/r30.md` before you start session 4. This is the long job. If you are about to be cut off, write how far the run got and stop.

Clone this bundle fresh. `uv sync --extra dev`. Then:

`uv run python -m pytest -q -m "not docker and not slow"`

Report passed, failed, skipped, and the first failure if there is one. An OCCT crash after a green summary (exit 3221225477 or -1073741819) is not a failure. Do not run the docker marker, the slow marker, or any OpenFOAM case.
