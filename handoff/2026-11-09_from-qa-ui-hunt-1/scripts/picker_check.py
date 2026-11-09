"""ui-hunt-1: visible Design picker text while edited_stale (Design sub-tab, Expert + Simple). No runs."""
import json, os, sys
from playwright.sync_api import sync_playwright
URL = f"http://127.0.0.1:{os.environ.get('QA_PORT','8812')}/"; R = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1366, "height": 768}); pg.goto(URL, wait_until="networkidle"); pg.wait_for_timeout(5000)
    for m in ("expert", "simple"):
        pg.evaluate(f"() => {{ window.trame.state.set('fan_subtab','design'); window.trame.state.set('ui_mode','{m}'); }}"); pg.wait_for_timeout(1500)
        pg.evaluate("() => window.scrollTo(0,0)")
        sel = pg.locator(".v-select:visible", has_text="based on")
        if not sel.count(): sel = pg.locator(".v-select:visible", has_text="Design")
        R[m] = {"edited_stale": pg.evaluate("() => window.trame.state.get('edited_stale')"), "e_n_blades": pg.evaluate("() => window.trame.state.get('e_n_blades')"),
                "picker": sel.first.inner_text().replace("\n", " | ")[:160] if sel.count() else None,
                "preview_caption_says_stock_loaded": "Stock reference loaded" in pg.evaluate("() => document.body.innerText"),
                "stale_note_visible": "Edited since assessment" in pg.evaluate("() => document.body.innerText")}
        pg.screenshot(path=f"{sys.argv[2]}/09_edited_picker_{m}_1366.png")
    b.close()
json.dump(R, open(sys.argv[1], "w"), indent=1, ensure_ascii=False); print(json.dumps(R, indent=1, ensure_ascii=False))
