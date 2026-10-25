# r20 D: README install-guide dry run on clean Linux (R3.3)

grok QA bot, 2026-10-21 08:38–08:40 MDT. Prereg `2c4380d`. Step log: `docs/qa/r20/r20-D-install-dryrun-log.csv`.

## Setup
- **Guide:** README "Install" on master 027ebcb. The bundle's HEAD, `r33-install-guide` fe899cd, has a
  **byte-identical README**, and master already merges it.
- **Kimball's PC working tree** is on `r33-install-guide`, not master. That is only noted; it changes nothing here.
- **Machine and user:**
  - Debian 13, system Python 3.13.5, git and curl, **no Docker**;
  - a new throwaway user `fsdry` with an empty HOME, and a fresh `git clone` of the bundle in a new `mktemp -d`;
  - `env -i PATH=/usr/bin:/bin`, with a new login shell per step (= "restart the shell").
- **No Docker was installed**, by rule.

## Result
The guide works on a clean Linux box. uv, Python 3.12 and every package installed, the cockpit served HTTP 200 in
12 s, and the optional UI test passed (6/6). That is with three small doc fixes and Docker untested.

**The brief's stop point** ("first step that fails or is unclear") is **step 2, `git clone <this-repo>`**. It has no
URL, so I supplied the bundle. I logged that and carried on, as pre-registered.

| step | grade | what happened |
|---|---|---|
| 1 install uv | PASS | uv 0.13.4 to `~/.local/bin`; found after the shell restart |
| 2 clone | AMBIGUOUS | `<this-repo>` has no URL (and the repo may be private) |
| 2 `cd Fan-simulator` | AMBIGUOUS | the literal command fails (the folder is `fansim` from the bundle); the comment "or whatever you named the folder" covers it |
| 2 `uv sync --extra dev` | PASS | fetched CPython 3.12.15 and installed 109 packages in 3.5 s; `import cadquery` OK |
| 3 Docker | WOULD-RUN | `docker` absent. The Linux bullet gives no install link or distro hint (Windows gets one) |
| 4 cockpit | PASS with doc error | it printed **`http://127.0.0.1:8080/`** and returned HTTP 200 at 12 s, but the README says "usually `http://localhost:9001`". `scripts/cockpit.py` defaults to `--port 8080` |
| 4 Assess | WOULD-RUN | it needs Docker. The README says "takes several minutes"; the code's own note says "typically 30–40 min free+load" |
| Troubleshooting "Docker not running" | AMBIGUOUS | no such text exists in the code (that's R3.4, not landed). With Docker absent, `image_available()` raises `FileNotFoundError: … 'docker'`, so Assess would read "Assess failed: FileNotFoundError: … 'docker'" (from code reading, not clicked) |
| optional UI test | PASS | 6 passed in 4.1 s |
| optional full fast suite | not run | MemAvailable 4.6 GB < 10 GB (shared box), as pre-registered |

## Other observations
- **Headless VTK:** with no DISPLAY, the cockpit logs "bad X server connection", "Failed to load EGL" and "libOSMesa
  not found". The server still serves. Whether the 3-D view renders on a headless or Wayland-only box wasn't checked
  in a browser, and the guide lists no system GL packages. This is a risk, not a finding.
- **Nothing to fix:**
  - `runs/opt_mountable` doesn't exist on a fresh clone, and the cockpit starts without complaint, as the README says.
  - The pre-check saw the box's own `/usr/local/bin/uv` through `/etc/profile`. That's a box artefact; after step 1
    the user's uv wins.

## Proposed README fixes (QA-53)
1. Replace `<this-repo>` with the real clone URL, and `cd Fan-simulator` with the folder that URL produces.
2. Change "usually `http://localhost:9001`" to `http://127.0.0.1:8080` (or change the default port).
3. Change "takes several minutes" to "typically 30–40 minutes".
4. Add a Linux link (docs.docker.com/engine/install) and `sudo usermod -aG docker $USER`.
5. Add a troubleshooting row for `FileNotFoundError: … 'docker'` (Docker not installed), until R3.4's badge lands.
6. Add a step-2 check, e.g. `uv run python -c "import fansim"`.
