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

And it releases a gone client's image-push subscriptions (UI-18): the VTK web protocol counts
``viewport.image.push.observer.add`` calls per view but has no disconnect hook, so a tab that
vanished without ``observer.remove`` kept its views rendering and pushing images forever. The
handler now remembers each client's adds/removes and, on close, calls the protocol's own
``observer.remove`` for whatever that client still held.
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
# wait_for's timer cannot fire while VTK blocks the loop. When the loop resumes, the
# callback is already overdue. A real stalled client expires within a few ms of the
# deadline (loop was running). More than this overdue → server-side starvation, not
# a tab that stopped reading.
STARVE_OVERDUE_S = 0.2

OBSERVER_ADD = "viewport.image.push.observer.add"
OBSERVER_REMOVE = "viewport.image.push.observer.remove"

_installed = False
_locks: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
_dead: weakref.WeakSet = weakref.WeakSet()


def send_timeout_s() -> float:
    try:
        return max(1.0, float(os.environ.get(ENV_SEND_TIMEOUT, DEFAULT_SEND_TIMEOUT_S)))
    except ValueError:
        return DEFAULT_SEND_TIMEOUT_S


def _timeout_was_loop_starvation(elapsed: float, timeout: float, n_sent: int) -> bool:
    """True when wait_for expired late because the event loop was stuck, not the client."""
    return n_sent == 0 and (elapsed - timeout) >= STARVE_OVERDUE_S


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
    loop = asyncio.get_running_loop()
    n_sent = [0]

    async def _send():
        async with lock:
            for chunk in chunks:
                if ws in _dead:
                    return
                await ws.send_bytes(chunk)
                n_sent[0] += 1

    t0 = loop.time()
    try:
        try:
            await asyncio.wait_for(_send(), timeout)
        except (TimeoutError, asyncio.TimeoutError):
            elapsed = loop.time() - t0
            if _timeout_was_loop_starvation(elapsed, timeout, n_sent[0]):
                _log.warning(
                    "websocket send waited %.0f s because the 3-D view blocked the server; "
                    "retrying, not dropping the tab",
                    elapsed,
                )
                try:
                    await asyncio.wait_for(_send(), timeout)
                    return
                except (TimeoutError, asyncio.TimeoutError):
                    pass
            if ws not in _dead:  # sends queued behind the stuck one time out too; say it once
                _log.warning(
                    "websocket tab stopped reading for %.0f s — disconnected it. "
                    "Hard-refresh the browser (Ctrl+Shift+R) or open the cockpit URL in a new tab.",
                    timeout,
                )
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


def _observed(handler) -> dict:
    if not hasattr(handler, "_fansim_observed"):
        handler._fansim_observed = {}
    return handler._fansim_observed


def _track_observers(handler, rpc, client_id) -> None:
    """Count this client's image-push subscriptions per view id (UI-18)."""
    if not isinstance(rpc, dict):
        return
    method, args = rpc.get("method"), rpc.get("args") or []
    if method not in (OBSERVER_ADD, OBSERVER_REMOVE) or not args:
        return
    views = _observed(handler).setdefault(client_id, {})
    view = str(args[0])
    views[view] = views.get(view, 0) + (1 if method == OBSERVER_ADD else -1)
    if views[view] <= 0:
        del views[view]


def release_observers(handler, client_id) -> int:
    """Undo the subscriptions a closed client still held; returns how many were released."""
    views = _observed(handler).pop(client_id, {})
    entry = getattr(handler, "functionMap", {}).get(OBSERVER_REMOVE)
    if not views or entry is None:
        return 0
    obj, func = entry
    released = 0
    for view, count in views.items():
        for _ in range(count):
            try:
                func(obj, view)
                released += 1
            except Exception as exc:  # noqa: BLE001 — view already gone; nothing to release
                _log.debug("observer release for view %s skipped: %s", view, exc)
    if released:
        _log.info("released %d image subscription(s) of a closed client", released)
    return released


def install() -> None:
    """Patch wslink's handler once per process (idempotent). ``FANSIM_WS_GUARD=0`` skips it."""
    global _installed  # noqa: PLW0603
    if _installed or os.environ.get("FANSIM_WS_GUARD", "1") == "0":
        return
    from wslink.protocol import WslinkHandler

    orig_on_close = WslinkHandler.onClose
    orig_on_complete = WslinkHandler.onCompleteMessage

    async def on_complete_message(self, rpc, client_id):
        _track_observers(self, rpc, client_id)
        await orig_on_complete(self, rpc, client_id)

    async def on_close(self, client_id):
        self.unchunkers.setdefault(client_id, None)  # handshake never completed (UI-17)
        try:
            await orig_on_close(self, client_id)
        finally:
            release_observers(self, client_id)

    WslinkHandler.sendWrappedMessage = _send_wrapped_message
    WslinkHandler.sendWrappedError = _send_wrapped_error
    WslinkHandler.onCompleteMessage = on_complete_message
    WslinkHandler.onClose = on_close
    _installed = True
