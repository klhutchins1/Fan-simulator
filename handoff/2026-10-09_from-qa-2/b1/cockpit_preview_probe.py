"""Headless B1 repro (QA only): trigger the Fan-tab Preview in the running cockpit and measure
event-loop responsiveness from a 2nd session (trame.state.get round trip every 0.25 s), logging
preview_busy / preview_pct / caption. Usage: SERVER_PID=.. python cockpit_preview_probe.py <cup 0|1>"""
import asyncio, aiohttp, os, sys, time
exec(open(os.path.join(os.environ["WS_DIR"], "ws_stress.py")).read().split("async def main")[0])
CUP = sys.argv[1] == "1"

async def m():
    async with aiohttp.ClientSession() as h:
        a, sa, st = await open_session(h, observe_views=True)   # "browser" with the 3-D view
        b, sb, _ = await open_session(h)                          # probe
        print("design loaded:", st["state"].get("e_tip_radius"), "cup was", st["state"].get("preview_motor_cup"))
        await sa.rpc(a, "trame.state.update", [[{"key": "preview_motor_cup", "value": CUP}]])
        t0 = time.time()
        await sa.send(a, {"wslink": "1.0", "id": f"rpc:{sa.cid}:999", "method": "trame.trigger",
                          "args": ["trigger__11", [], {}], "kwargs": {}})
        last, worst, seen_busy = None, (0, 0), False
        while time.time() - t0 < 240:
            t = time.time()
            S = (await sb.rpc(b, "trame.state.get", [], timeout=60))["state"]
            rt = time.time() - t
            if rt > worst[0]: worst = (round(rt, 2), round(t - t0, 1))
            row = (S.get("preview_busy"), S.get("preview_pct"), (S.get("preview_msg") or "")[:70].replace("\n", " "))
            if row != last or rt > 1.0:
                print(f"t={t-t0:6.2f}s rtt={rt:5.2f}s busy={row[0]} pct={row[1]} msg={row[2]!r}", flush=True); last = row
            seen_busy |= bool(row[0])
            if seen_busy and not row[0]: break
            await asyncio.sleep(0.25)
        print("worst loop round-trip", worst[0], "s at t=", worst[1], "s; total", round(time.time() - t0, 1), "s")
        await sa.rpc(a, "trame.state.update", [[{"key": "preview_motor_cup", "value": False}]])
        S = (await sb.rpc(b, "trame.state.get", []))["state"]; print("reset: preview_motor_cup =", S.get("preview_motor_cup"))
        await a.close(); await b.close()
asyncio.run(m())
