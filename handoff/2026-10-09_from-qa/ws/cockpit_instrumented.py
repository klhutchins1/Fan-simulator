"""QA-only launcher: runs the repo cockpit unchanged, plus a 2 s asyncio-task census to a TSV."""
import asyncio, collections, os, sys, time
REPO = os.environ.get("QA_REPO", os.getcwd())
sys.path.insert(0, REPO)
from fansim.cockpit.app import build_server

run = sys.argv[1]; port = int(sys.argv[2]); out = sys.argv[3]
server = build_server(run, None)
T0 = time.time()

async def census():
    with open(out, "a") as f:
        while True:
            try:
                tasks = asyncio.all_tasks()
                names = collections.Counter(
                    getattr(t.get_coro(), "__qualname__", str(t.get_coro()))[:60] for t in tasks)
                top = ";".join(f"{k}={v}" for k, v in names.most_common(4))
                top += "\t" + _server_census()
                f.write(f"{time.time()-T0:.0f}\t{len(tasks)}\t{top}\n"); f.flush()
            except Exception as e:  # noqa
                f.write(f"err {e}\n")
            await asyncio.sleep(2)

_cache = {}
def _server_census():
    """connections / unchunkers / image-push observerCount, found once via gc (QA only)."""
    import gc
    if "h" not in _cache or "img" not in _cache:
        for o in gc.get_objects():
            n = type(o).__name__
            if n.endswith("WsHandler") or n == "WslinkHandler": _cache["h"] = o
            elif "ImageDelivery" in n or "trackingViews" in (type(o).__dict__ if False else {}):
                try:
                    if isinstance(object.__getattribute__(o, "tracking_views"), dict): _cache["img"] = o
                except Exception: pass
    h, img = _cache.get("h"), _cache.get("img")
    conns = len(h.connections) if h else -1
    unch = len(h.unchunkers) if h else -1
    obs = {k: v.get("observerCount") for k, v in img.tracking_views.items()} if img else {}
    return f"conns={conns}\tunchunkers={unch}\timg={'y' if img else 'n'}\tobservers={obs}"

_keep = []
def _ready(**_):
    print("[qa] census starting", flush=True)
    _keep.append(asyncio.ensure_future(census()))
server.controller.on_server_ready.add(_ready)
server.start(port=port, host="127.0.0.1", open_browser=False)
