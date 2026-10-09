"""One stalled websocket client must not block the others (QA UI-16 / UI-17)."""

from __future__ import annotations

import asyncio

import pytest

from fansim.cockpit import ws_guard


class _Transport:
    def __init__(self):
        self.aborted = False

    def abort(self):
        self.aborted = True


class _Req:
    def __init__(self):
        self.transport = _Transport()


class _WS:
    def __init__(self, stalled: bool = False):
        self.stalled, self.closed, self.got = stalled, False, []
        self._req = _Req()

    async def send_bytes(self, chunk):
        if self.stalled:
            await asyncio.sleep(3600)      # TCP buffer full: drain never returns
        self.got.append(chunk)


class _Monitor:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def network_call_completed(self):
        pass


class _Handler:
    network_monitor = _Monitor()


def test_stalled_client_is_aborted_and_others_still_receive(monkeypatch):
    monkeypatch.setenv(ws_guard.ENV_SEND_TIMEOUT, "1")
    good, stuck = _WS(), _WS(stalled=True)

    async def run():
        t0 = asyncio.get_running_loop().time()
        await ws_guard._fan_out(_Handler(), b"hello", [stuck, good])
        await ws_guard._fan_out(_Handler(), b"again", [stuck, good])
        return asyncio.get_running_loop().time() - t0

    elapsed = asyncio.run(run())
    assert len(good.got) == 2                     # healthy client got both messages
    assert stuck._req.transport.aborted           # stalled one dropped, not waited on forever
    assert elapsed < 3.0                          # one timeout window, then skipped


def test_messages_keep_their_order_per_client():
    ws = _WS()

    async def run():
        await asyncio.gather(*(ws_guard._fan_out(_Handler(), f"m{i}".encode(), [ws])
                               for i in range(20)))

    asyncio.run(run())
    assert [bytes(c)[12:] for c in ws.got] == [f"m{i}".encode() for i in range(20)]


def test_install_is_idempotent_and_on_close_tolerates_unfinished_handshake():
    from wslink.protocol import WslinkHandler

    ws_guard.install()
    first = WslinkHandler.onClose
    ws_guard.install()
    assert WslinkHandler.onClose is first

    h = WslinkHandler.__new__(WslinkHandler)
    h.unchunkers, h.serverProtocol = {}, None     # 'curl /ws': no unchunker was ever created
    asyncio.run(h.onClose("never-prepared"))       # used to raise KeyError (UI-17)


@pytest.mark.parametrize("raw, want", [("", 15.0), ("0.2", 1.0), ("30", 30.0), ("x", 15.0)])
def test_send_timeout_env(monkeypatch, raw, want):
    monkeypatch.setenv(ws_guard.ENV_SEND_TIMEOUT, raw)
    if raw == "":
        monkeypatch.delenv(ws_guard.ENV_SEND_TIMEOUT)
    assert ws_guard.send_timeout_s() == want
