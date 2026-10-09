#!/usr/bin/env bash
# QA websocket regression suite (UI-16/17/18). Usage: ws_suite.sh <label> <port> <census_tsv> <server_log>
set -u
L=$1; PORT=$2; CENSUS=$3; SLOG=$4
PY=${PY:-python}; D=$(cd "$(dirname "$0")" && pwd); export D
SP=$(ss -ltnp | grep "127.0.0.1:$PORT " | sed -E 's/.*pid=([0-9]+).*/\1/')
export WS_URL=ws://127.0.0.1:$PORT/ws SERVER_PID=$SP
cen() { tail -1 "$CENSUS" | cut -f4-; }
echo "== $L server pid $SP; census: $(cen)"
echo "-- A: 20x plain GET /ws (UI-17)"
k0=$(grep -c KeyError "$SLOG"); for i in $(seq 20); do curl -s -o /dev/null "http://127.0.0.1:$PORT/ws"; done; sleep 3
echo "KeyError lines +$(( $(grep -c KeyError "$SLOG") - k0 )); census: $(cen)"
echo "-- B: 30 sessions with image observer, all aborted without close frame (UI-18)"
METRICS=/tmp/ws_$L.B.tsv OBSERVE=1 "$PY" - <<'PY'
import asyncio, aiohttp, os
exec(open(os.environ["D"] + "/ws_stress.py").read().split("async def main")[0])
async def m():
    async with aiohttp.ClientSession() as h:
        for i in range(30):
            ws, s, st = await open_session(h, observe_views=True); hard_close(ws)
asyncio.run(m())
PY
sleep 4; echo "census after B: $(cen)"
echo "-- C: 1 stalled client + 200 image pushes (UI-16)"
STALL_ROUNDS=${STALL_ROUNDS:-4} RECOVER_ROUNDS=2 timeout 300 "$PY" "$D/ws_stall.py" main 1 200 2>&1 | cut -c1-220
pkill -9 -f "ws_stall.py child" 2>/dev/null; sleep 3; echo "census after C: $(cen)"
echo "-- D: ${CYCLES:-500} open/close cycles (clean/no-exit/abort/RST/concurrent)"
METRICS=/tmp/ws_$L.D.tsv "$PY" "$D/ws_stress.py" "${CYCLES:-500}" 25 2>&1 | grep -E "initial|END|ERR|FAIL|STOP" | cut -c1-200
head -1 /tmp/ws_$L.D.tsv >/dev/null; sed -n '2p;$p' /tmp/ws_$L.D.tsv
sleep 4; echo "census after D: $(cen)"
echo "-- log: KeyError=$(grep -c KeyError "$SLOG") closing_transport=$(grep -c 'Cannot write to closing transport' "$SLOG") no_pong=$(grep -c 'No PONG' "$SLOG") dropped_stalled=$(grep -c 'not reading for' "$SLOG") released=$(grep -c 'released .* image subscription' "$SLOG")"
