# Fan-simulator recovery notes (from Cursor conversation cache)

**Status:** `E:\Projects\programming_2\Fan-simulator` was on a drive that died.
This file is reconstructed from agent conversation memory / SearchConversations
snippets — **not** a byte-for-byte restore of the repo.

**Date written:** 2026-09-12
**Also see:** `CHAT_RECOVERY/` in this tree for the structured pack.

(Full copy of earlier notes — superseded in detail by CHAT_RECOVERY 01–06.)

## What we could / could not find

| Source | Result |
|--------|--------|
| Workspace `E:\Projects\programming_2\Fan-simulator` | Missing |
| Public GitHub mirror named Fan-simulator / fansim (Kimball) | Not found |
| Cursor conversation index | Partial architecture / audit text still searchable |
| Commits remembered | `b360dde`, `a110f76` (local master; may never have been pushed) |

## Project identity

- **Name:** Fan-simulator (`fansim` Python package)
- **Purpose:** Axial / mixed-flow fan design cockpit + Optuna multi-objective CFD optimization (OpenFOAM in Docker), BEM/BEMT screens, acoustics proxies, printability gates (A12x25 etc.)
- **Run style:** `uv run pytest` / `uv run python` / `uv run --extra optim python scripts/...`
- **CFD image:** `opencfd/openfoam-default:2406`

## Honest limit

Cursor chat cache retains **descriptions and snippets**, not a full git object store.
**Cannot recreate the full application source from memory alone.**
