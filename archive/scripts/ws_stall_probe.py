"""Reproduce QA UI-16: one stalled websocket client must not freeze every cockpit session.

Against a running cockpit (default http://127.0.0.1:8092):

  1. a "frozen tab" client completes the wslink handshake, then stops reading (its event loop is
     blocked, like a sleeping browser tab or a dropped Wi-Fi link);
  2. a "busy" client pushes large state updates, which the server broadcasts to every other client,
     so the frozen client's TCP buffers fill;
  3. a probe opens fresh sessions every few seconds and times the ``wslink.hello`` reply.

PASS = every probe after the frozen client fills up still gets its hello within ``--probe-timeout``.

    uv run python scripts/ws_stall_probe.py --url http://127.0.0.1:8092 --seconds 90
"""

from __future__ import annotations

import argparse
import asyncio
import json
import multiprocessing as mp
import sys
import time

import aiohttp
import msgpack

from wslink.chunking import UnChunker, generate_chunks

SECRET = "wslink-secret"  # trame default


def _pack(rpc_id: str, method: str, args: list) -> list[bytes]:
    msg = msgpack.packb({"wslink": "1.0", "id": rpc_id, "method": method, "args": args,
                         "kwargs": {}})
    return list(generate_chunks(msg, 0))


async def _hello(ws) -> dict:
    for chunk in _pack("system:c0:0", "wslink.hello", [{"secret": SECRET}]):
        await ws.send_bytes(chunk)
    un = UnChunker()
    un.set_max_message_size(1 << 30)
    async for msg in ws:
        if msg.type != aiohttp.WSMsgType.BINARY:
            continue
        full = un.process_chunk(msg.data)
        if full is not None and full.get("id") == "system:c0:0":
            return full
    raise RuntimeError("socket closed before hello reply")


def _frozen_client(url: str, ready) -> None:
    """Handshake, ask for the state (so the server treats us as a live client), then block."""

    async def run():
        async with aiohttp.ClientSession() as s, s.ws_connect(url + "/ws", max_msg_size=0) as ws:
            await _hello(ws)
            for chunk in _pack("rpc:1", "trame.state.get", []):
                await ws.send_bytes(chunk)
            ready.set()
            time.sleep(3600)  # blocks the loop: nothing is read from the socket any more

    asyncio.run(run())


async def _busy_client(url: str, stop: asyncio.Event, blob_kb: int) -> int:
    sent = 0
    async with aiohttp.ClientSession() as s, s.ws_connect(url + "/ws", max_msg_size=0) as ws:
        await _hello(ws)

        async def drain():
            async for _ in ws:
                pass

        reader = asyncio.create_task(drain())
        while not stop.is_set():
            blob = f"{sent:08d}" + "x" * (blob_kb * 1024)
            for chunk in _pack(f"rpc:u{sent}", "trame.state.update",
                               [[{"key": "ws_stall_probe_blob", "value": blob}]]):
                await ws.send_bytes(chunk)
            sent += 1
            await asyncio.sleep(0.05)
        reader.cancel()
    return sent


async def _probe(url: str, timeout: float) -> float | None:
    t0 = time.perf_counter()
    try:
        async with aiohttp.ClientSession() as s:
            async with s.ws_connect(url + "/ws", max_msg_size=0) as ws:
                await asyncio.wait_for(_hello(ws), timeout)
        return time.perf_counter() - t0
    except (TimeoutError, asyncio.TimeoutError, aiohttp.ClientError, RuntimeError):
        return None


async def main_async(args) -> dict:
    ready = mp.Event()
    frozen = mp.Process(target=_frozen_client, args=(args.url, ready), daemon=True)
    frozen.start()
    if not ready.wait(30):
        raise SystemExit("frozen client never completed its handshake")
    stop = asyncio.Event()
    busy = asyncio.create_task(_busy_client(args.url, stop, args.blob_kb))
    probes = []
    t0 = time.time()
    while time.time() - t0 < args.seconds:
        await asyncio.sleep(args.every)
        dt = await _probe(args.url, args.probe_timeout)
        probes.append({"t": round(time.time() - t0, 1), "hello_s": None if dt is None else round(dt, 3)})
        print(json.dumps(probes[-1]), flush=True)
    stop.set()
    try:
        sent = await asyncio.wait_for(busy, 10)
    except (TimeoutError, asyncio.TimeoutError):
        busy.cancel()
        sent = -1  # the busy client itself was stuck
    except (aiohttp.ClientError, ConnectionError) as exc:
        sent = f"busy client lost its connection: {exc}"
    frozen.terminate()
    late = [p for p in probes if p["t"] >= args.grace]
    failed = [p for p in late if p["hello_s"] is None]
    return {"updates_sent": sent, "probes": len(probes), "failed_after_grace": len(failed),
            "verdict": "PASS" if late and not failed else "FAIL"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default="http://127.0.0.1:8092")
    ap.add_argument("--seconds", type=float, default=90.0)
    ap.add_argument("--every", type=float, default=5.0, help="seconds between probes")
    ap.add_argument("--probe-timeout", type=float, default=10.0)
    ap.add_argument("--grace", type=float, default=0.0,
                    help="ignore probes before this many seconds (e.g. a send-timeout window)")
    ap.add_argument("--blob-kb", type=int, default=256)
    args = ap.parse_args()
    out = asyncio.run(main_async(args))
    print(json.dumps(out), flush=True)
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
