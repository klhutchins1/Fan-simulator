"""Keep one stalled browser tab from freezing every cockpit session (QA UI-16, UI-17).

wslink (2.5.x) sends every message to every client inside ONE global ``asyncio.Lock``, one client
after another, with no timeout. A client that stops reading (sleeping tab, frozen laptop, dropped
Wi-Fi) fills its TCP buffer; its ``send_bytes`` then never returns, the lock is never released, and
no other client — including a new tab's ``wslink.hello`` — gets a reply until that client is
killed. aiohttp's heartbeat does not save it: on a missed PONG it calls ``transport.close()``, which
waits to flush the very buffer that is stuck.

``install()`` replaces the two send methods with versions that:

- lock per websocket instead of globally (aiohttp still must not run two sends on one socket,
  aio-libs/aiohttp#2934), so a stalled client only delays its own messages;
- bound each client's send by ``FANSIM_WS_SEND_TIMEOUT`` seconds (default 15) and, on timeout,
  ABORT that client's transport (drops the buffer; the client's handler loop then ends and wslink
  cleans the connection up as for any disconnect). Later messages to it are skipped.

It also makes ``onClose`` tolerate a connection whose handshake never completed (``curl /ws``):
wslink registers the connection before ``prepare()`` but only creates its unchunker after, so
``onClose`` raised ``KeyError`` and leaked the ``connections`` entry (UI-17).
"""

from __future__ import annotations

import asyncio
import logging
import os
import weakref

import msgpack

_log = logging.getLogger(__name__)

ENV_SEND_TIMEOUT = "FANSIM_WS_SEND_TIMEOUT"
DEFAULT_SEND_TIMEOUT_S = 15.0

_installed = False
_locks: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
_dead: weakref.WeakSet = weakref.WeakSet()


def send_timeout_s() -> float:
    try:
        return max(1.0, float(os.environ.get(ENV_SEND_TIMEOUT, DEFAULT_SEND_TIMEOUT_S)))
    except ValueError:
        return DEFAULT_SEND_TIMEOUT_S


def _abort(ws) -> None:
    """Drop the connection now (no close handshake, no flush of the stuck buffer)."""
    _dead.add(ws)
    req = getattr(ws, "_req", None)
    transport = getattr(req, "transport", None) if req is not None else None
    if transport is not None:
        transport.abort()


async def _send_chunks(ws, chunks: list[bytes], timeout: float) -> None:
    if ws is None or ws in _dead or ws.closed:
        return
    lock = _locks.setdefault(ws, asyncio.Lock())

    async def _send():
        async with lock:
            for chunk in chunks:
                if ws in _dead:
                    return
                await ws.send_bytes(chunk)

    try:
        await asyncio.wait_for(_send(), timeout)
    except (TimeoutError, asyncio.TimeoutError):
        if ws not in _dead:  # sends queued behind the stuck one time out too; say it once
            _log.warning("websocket client not reading for %.0f s; dropping it so other sessions "
                         "keep working", timeout)
        _abort(ws)
    except (ConnectionError, RuntimeError) as exc:  # closing/closed transport
        _log.debug("websocket send to a closing client skipped: %s", exc)
        _dead.add(ws)


async def _fan_out(handler, packed: bytes, websockets) -> None:
    from wslink.chunking import generate_chunks
    from wslink.protocol import MAX_MSG_SIZE

    chunks = list(generate_chunks(packed, MAX_MSG_SIZE))
    timeout = send_timeout_s()
    with handler.network_monitor:
        await asyncio.gather(*(_send_chunks(ws, chunks, timeout) for ws in websockets))
    handler.network_monitor.network_call_completed()


async def _send_wrapped_message(self, rpcid, content, method="", client_id=None,
                                skip_last_active_client=False):
    from wslink.protocol import RESULT_SERIALIZE_ERROR

    try:
        packed = msgpack.packb({"wslink": "1.0", "id": rpcid, "result": content})
    except Exception:  # noqa: BLE001 — same contract as wslink: report, don't include the content
        with self.network_monitor:
            await self.sendWrappedError(rpcid, RESULT_SERIALIZE_ERROR,
                                        "Method result cannot be serialized", method,
                                        client_id=client_id)
        return
    await _fan_out(self, packed, self.getAuthenticatedWebsockets(client_id, skip_last_active_client))


async def _send_wrapped_error(self, rpcid, code, message, data=None, client_id=None):
    wrapper = {"wslink": "1.0", "id": rpcid, "error": {"code": code, "message": message}}
    if data:
        wrapper["error"]["data"] = data
    try:
        packed = msgpack.packb(wrapper)
    except Exception:  # noqa: BLE001
        del wrapper["error"]["data"]
        packed = msgpack.packb(wrapper)
    if client_id:
        websockets = [self.connections.get(client_id)]
    else:
        websockets = list(self.connections.values())
    await _fan_out(self, packed, websockets)


def install() -> None:
    """Patch wslink's handler once per process (idempotent)."""
    global _installed  # noqa: PLW0603
    if _installed:
        return
    from wslink.protocol import WslinkHandler

    orig_on_close = WslinkHandler.onClose

    async def on_close(self, client_id):
        self.unchunkers.setdefault(client_id, None)  # handshake never completed (UI-17)
        await orig_on_close(self, client_id)

    WslinkHandler.sendWrappedMessage = _send_wrapped_message
    WslinkHandler.sendWrappedError = _send_wrapped_error
    WslinkHandler.onClose = on_close
    _installed = True
