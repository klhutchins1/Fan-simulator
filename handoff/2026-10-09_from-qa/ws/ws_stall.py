"""Stalled-client scenario: K clients finish the browser handshake + image observer, then freeze
(SIGSTOP: TCP stays open, nothing is read, no pong). A live client then asks for image pushes and
we check whether a FRESH session can still complete wslink.hello + trame.state.get."""
import asyncio, os, signal, subprocess, sys, time
import aiohttp
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ws_stress.py")).read().split("async def main")[0])

async def child():
    async with aiohttp.ClientSession() as h:
        ws, s, st = await open_session(h, observe_views=True)
        print("child ready", s.cid, flush=True)
        os.kill(os.getpid(), signal.SIGSTOP)
        await asyncio.sleep(3600)

async def timed_probe(h, to=20):
    t = time.time()
    try:
        ok, ps, nk = await asyncio.wait_for(probe(h), to); return ok, round(time.time()-t, 2)
    except Exception as e:
        return f"FAIL {type(e).__name__}", round(time.time()-t, 2)

async def main():
    K = int(sys.argv[2]); PUSHES = int(sys.argv[3])
    kids = []
    for _ in range(K):
        p = subprocess.Popen([sys.executable, __file__, "child"], stdout=subprocess.PIPE, text=True, env=os.environ)
        p.stdout.readline(); kids.append(p)
    print(f"{K} stalled clients", "server", proc_metrics(), flush=True)
    async with aiohttp.ClientSession() as h:
        ws, s, st = await open_session(h, observe_views=True)
        vid = view_ids(st)[0]
        t = time.time(); done = 0
        async def pusher():
            nonlocal done
            for i in range(PUSHES):
                await s.rpc(ws, "viewport.image.push", [{"view": vid}], timeout=60); done += 1
        pt = asyncio.ensure_future(pusher())
        for k in range(int(os.environ.get('STALL_ROUNDS', '8'))):
            await asyncio.sleep(5)
            print(f"t={time.time()-t:.0f}s alive_stalled={sum(p.poll() is None for p in kids)} pushes_done={done} probe={await timed_probe(h)} server={proc_metrics()}", flush=True)
            if pt.done(): break
        print("pusher:", "done" if pt.done() and not pt.exception() else repr(pt.exception() if pt.done() else "STUCK")[:200], flush=True)
        pt.cancel()
    for p in kids: p.kill()
    for k in range(int(os.environ.get('RECOVER_ROUNDS', '4'))):
        await asyncio.sleep(5)
        async with aiohttp.ClientSession() as h:
            print(f"after-kill t+{5*(k+1)}s probe={await timed_probe(h)} server={proc_metrics()}", flush=True)

if sys.argv[1] == "child": asyncio.run(child())
else: asyncio.run(main())
