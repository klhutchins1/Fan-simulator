"""Reconnect stress for the trame/wslink cockpit (QA only). Mimics the browser handshake:
WS upgrade on /ws -> wslink.hello(secret) -> trame.state.get -> lifecycle client_connected
(-> optional image-push observer add for remote views) -> close (clean | abort | rst | stall)."""
import asyncio, json, os, random, socket, struct, sys, time
import aiohttp, msgpack
from wslink.chunking import generate_chunks, UnChunker

URL = os.environ.get("WS_URL", "ws://127.0.0.1:8080/ws")
PID = int(os.environ["SERVER_PID"]); METRICS = os.environ.get("METRICS", "ws_metrics.tsv")
PORT = int(URL.split(":")[2].split("/")[0])

def proc_metrics():
    st = open(f"/proc/{PID}/status").read()
    rss = int(st.split("VmRSS:")[1].split()[0]) // 1024
    thr = int(st.split("Threads:")[1].split()[0])
    fds = len(os.listdir(f"/proc/{PID}/fd"))
    socks = sum(1 for l in open(f"/proc/{PID}/net/tcp").read().splitlines()[1:]
                if l.split()[1].endswith(":%04X" % PORT))  # local server port (any state)
    return rss, thr, fds, socks

class Sess:
    def __init__(self): self.n = 0; self.cid = None; self.unch = UnChunker(); self.unch.set_max_message_size(1 << 30)
    async def send(self, ws, msg):
        for c in generate_chunks(msgpack.packb(msg), 4 * 1024 * 1024): await ws.send_bytes(c)
    async def rpc(self, ws, method, args, timeout=20):
        self.n += 1; rid = f"rpc:{self.cid}:{self.n}"
        await self.send(ws, {"wslink": "1.0", "id": rid, "method": method, "args": args, "kwargs": {}})
        return await self.wait(ws, rid, timeout)
    async def wait(self, ws, rid, timeout):
        end = time.time() + timeout
        while True:
            m = await ws.receive(timeout=max(0.1, end - time.time()))
            if m.type != aiohttp.WSMsgType.BINARY: raise RuntimeError(f"ws {m.type} {m.data!r}"[:200])
            full = self.unch.process_chunk(m.data)
            if full and full.get("id") == rid:
                if "error" in full: raise RuntimeError(f"rpc error {full['error']}"[:200])
                return full.get("result")

async def open_session(http, observe_views=False):
    ws = await http.ws_connect(URL, heartbeat=None, timeout=aiohttp.ClientWSTimeout(ws_receive=15, ws_close=5),
                               headers={"Origin": "http://127.0.0.1:8080"}, max_msg_size=0)
    s = Sess()
    await s.send(ws, {"wslink": "1.0", "id": "system:c0:0", "method": "wslink.hello",
                      "args": [{"secret": "wslink-secret"}], "kwargs": {}})
    r = await s.wait(ws, "system:c0:0", 15); s.cid = r["clientID"]
    state = await s.rpc(ws, "trame.state.get", [])
    await s.rpc(ws, "trame.lifecycle.update", ["client_connected"])
    if observe_views:
        for vid in view_ids(state):
            try: await s.rpc(ws, "viewport.image.push.observer.add", [vid], timeout=5)
            except Exception: pass
    return ws, s, state

def view_ids(state):
    st = (state or {}).get("state", {})
    return [str(v) for k, v in st.items() if k.startswith("P_") and k.endswith("Id")][:6]

def hard_close(ws, rst=False):
    tr = ws._writer.transport if hasattr(ws, "_writer") else None
    if tr is None: tr = ws._response.connection.transport
    if rst:
        sock = tr.get_extra_info("socket")
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
    tr.abort()

async def cycle(http, mode, observe):
    t = time.time()
    ws, s, state = await open_session(http, observe)
    if mode == "clean":
        await s.rpc(ws, "trame.lifecycle.update", ["client_exited"], timeout=5)
        await ws.close()
    elif mode == "close":
        await ws.close()
    elif mode in ("abort", "rst"):
        hard_close(ws, rst=(mode == "rst"))
    return time.time() - t

async def probe(http):
    t = time.time()
    ws, s, state = await open_session(http)
    nk = len((state or {}).get("state", {})); ok = nk > 100
    await ws.close()
    return ok, time.time() - t, nk

async def main():
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    batch = int(sys.argv[2]) if len(sys.argv) > 2 else 25
    observe = os.environ.get("OBSERVE", "1") == "1"
    random.seed(1)
    mf = open(METRICS, "a"); mf.write("t\tcycles\terrors\trss_mb\tthreads\tfds\tsocks8080\tprobe_ok\tprobe_s\tnkeys\n")
    t0 = time.time(); done = 0; errs = 0
    conn = aiohttp.TCPConnector(limit=0, force_close=True)
    async with aiohttp.ClientSession(connector=conn) as http:
        ok, ps, nk = await probe(http); print("initial probe", ok, f"{ps:.2f}s", nk, "keys", flush=True)
        while done < total:
            modes = random.choices(["clean", "close", "abort", "rst", "concurrent"], [3, 2, 3, 1, 1], k=batch)
            for m in modes:
                try:
                    if m == "concurrent":
                        k = random.randint(3, 6)
                        rs = await asyncio.gather(*[cycle(http, random.choice(["clean", "abort", "close"]), observe)
                                                    for _ in range(k)], return_exceptions=True)
                        bad = [r for r in rs if isinstance(r, Exception)]
                        errs += len(bad); done += k
                        if bad: print(f"cycle~{done} concurrent errs: {[repr(b)[:120] for b in bad[:2]]}", flush=True)
                    else:
                        await cycle(http, m, observe); done += 1
                except Exception as e:
                    errs += 1; done += 1; print(f"cycle {done} {m} ERR {e!r}"[:220], flush=True)
            await asyncio.sleep(1.0)
            try: ok, ps, nk = await probe(http)
            except Exception as e: ok, ps, nk = False, -1, 0; print(f"PROBE FAIL after {done}: {e!r}"[:220], flush=True)
            rss, thr, fds, socks = proc_metrics()
            row = f"{time.time()-t0:.0f}\t{done}\t{errs}\t{rss}\t{thr}\t{fds}\t{socks}\t{ok}\t{ps:.2f}\t{nk}"
            mf.write(row + "\n"); mf.flush(); print(row, flush=True)
            if not ok and os.environ.get("STOP_ON_FAIL", "1") == "1":
                print("STOP: fresh session failed", flush=True); break
    print("END", done, "cycles", errs, "errors", f"{time.time()-t0:.0f}s", flush=True)

asyncio.run(main())
