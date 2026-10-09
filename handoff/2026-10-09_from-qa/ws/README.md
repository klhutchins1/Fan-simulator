# Websocket regression scripts (UI-16 / UI-17 / UI-18), QA 2026-10-09

Linux-only (the stall test uses SIGSTOP). Run them with the repo venv, from the repo root.
They are plain clients of the cockpit's trame/wslink `/ws` endpoint. They mimic a browser:
`wslink.hello` (secret `wslink-secret`) → `trame.state.get` →
`trame.lifecycle.update client_connected` → `viewport.image.push.observer.add` for each remote
view id (`P_*Id` state keys).

| file | what |
|---|---|
| `ws_stress.py` | N open/close cycles in batches. Each cycle ends one of five ways: clean (`client_exited` + close), close without `client_exited`, TCP abort with no close frame, RST, or 3–6 overlapping sessions. After each batch, a fresh session must get the full state (>100 keys). It logs server RSS, threads, fds and port sockets to `$METRICS`. Env: `SERVER_PID` (required), `WS_URL` (default `ws://127.0.0.1:8080/ws`), `OBSERVE=1`, `STOP_ON_FAIL=1`. Args: `<cycles> <batch>`. |
| `ws_stall.py` | `main <K> <pushes>`: K child clients finish the handshake and image observer, then SIGSTOP themselves (a frozen tab). A live client then asks for `<pushes>` `viewport.image.push` calls. Every 5 s it probes whether a NEW session completes hello + state within 15 s. Then it kills the children and probes again. Env: `STALL_ROUNDS` (default 8), `RECOVER_ROUNDS` (default 4). |
| `ws_suite.sh` | `ws_suite.sh <label> <port> <census.tsv> <server.log>` runs four parts: A = 20 plain GETs on `/ws`; B = 30 observer sessions, all aborted; C = 1 stalled client + 200 pushes; D = `CYCLES` (default 500) stress cycles. It then prints log counts. Env: `PY` (python to use). |
| `cockpit_instrumented.py` | QA launcher: `QA_REPO=<repo> python cockpit_instrumented.py <run_dir> <port> <census.tsv>`. It runs `build_server` unchanged and every 2 s appends asyncio task counts plus the wslink handler's `connections` / `unchunkers` and the image-delivery protocol's `tracking_views[*].observerCount` (found via `gc`, QA-only) to the TSV. |
| `results/` | suite output on 961f953 (before) and d781894 (after) |

Typical run:
```
mkdir -p /tmp/empty_run
QA_REPO=$PWD nohup .venv/bin/python handoff/2026-10-09_from-qa/ws/cockpit_instrumented.py /tmp/empty_run 8080 /tmp/census.tsv > /tmp/cockpit.log 2>&1 &
sleep 30
PY=.venv/bin/python bash handoff/2026-10-09_from-qa/ws/ws_suite.sh run 8080 /tmp/census.tsv /tmp/cockpit.log
```

Pass criteria (what d781894 does):
- A: KeyError +0, `conns=0`.
- B: `observers={}` after the aborted sessions.
- C: every probe True (<1 s), and the stalled client is dropped about 15 s later (`not reading for 15 s` warning once).
- D: 0 errors, every probe True.

On 961f953, A gives +20 KeyErrors and `conns=20` (leaked). B gives `observers={'1': 30}`, growing to 538 after D. C fails every probe (15 s timeout) until the frozen client is killed.

Notes:
- The `released N image subscription(s)` line is logged at INFO, which the default cockpit logging does not print. Use the census `observers=` column instead.
- To turn this into a pytest regression check: start the server in a fixture on a free port, run part C with `STALL_ROUNDS=1`, and assert the probe succeeds. That takes about 25 s, so mark it `slow`.
