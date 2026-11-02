"""QA r24 (reused r22) A: layout probe for UI-27/UI-29 (visible viewer box, controls column). Usage: pwvenv/bin/python a_probe.py <out.json>"""
import json, sys
from playwright.sync_api import sync_playwright
JS = """() => {
 const vis = []; for (const c of document.querySelectorAll('canvas')) { const r = c.getBoundingClientRect();
   let e = c, chain = []; while (e && e !== document.body) { const q = e.getBoundingClientRect();
     chain.push({tag: e.tagName, cls: (e.className && e.className.baseVal === undefined ? e.className : '').slice(0, 60), x: q.x, y: q.y, w: q.width, h: q.height, bottom: q.bottom}); e = e.parentElement; }
   vis.push({canvas: {x: r.x, y: r.y, w: r.width, h: r.height}, chain: chain.slice(0, 8)}); }
 let col = null; for (const t of document.querySelectorAll('.v-tab')) { if (t.innerText.trim().toUpperCase() === 'LIBRARY' && t.offsetParent) {
   let e = t; while (e && !(e.className || '').toString().includes('v-col')) e = e.parentElement;
   if (e) { const q = e.getBoundingClientRect(); col = {cls: e.className, x: q.x, w: q.width}; } } }
 return {canvases: vis, controls_col: col, vw: innerWidth, vh: innerHeight}; }"""
R = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
    for w, h in ((1366, 768), (1920, 1080)):
        for m in ("simple", "expert"):
            ctx = b.new_context(viewport={"width": w, "height": h}); pg = ctx.new_page()
            pg.goto("http://127.0.0.1:8080/", wait_until="networkidle"); pg.wait_for_timeout(6000)
            if pg.evaluate("() => window.trame.state.get('ui_mode')") != m:
                pg.locator(".v-btn", has_text=m.upper()).first.click(); pg.wait_for_timeout(1000)
            R[f"{w}x{h}_{m}"] = pg.evaluate(JS); ctx.close()
    b.close()
json.dump(R, open(sys.argv[1], "w"), indent=1)
