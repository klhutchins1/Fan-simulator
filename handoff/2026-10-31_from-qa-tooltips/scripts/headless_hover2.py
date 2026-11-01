from playwright.sync_api import sync_playwright
import json
out = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1600, "height": 1000})
    pg.goto("http://127.0.0.1:8080/"); pg.wait_for_timeout(8000)
    pg.get_by_role("button", name="Expert", exact=True).first.click(); pg.wait_for_timeout(2000)
    for _ in range(3):
        t = pg.locator(".v-expansion-panel-title:visible")
        for i in range(t.count()):
            if t.nth(i).get_attribute("aria-expanded") == "false":
                t.nth(i).click(); pg.wait_for_timeout(250)
    for lab in ["Hub profile", "Application (hose resistance)", "Print material", "Fan model (hub)",
                "Allow intake overbuild (+Z)", "Fit hub to the motor", "Sickle leading edge"]:
        loc = pg.locator(f".v-input:has(label:has-text('{lab}'))").first
        try:
            loc.scroll_into_view_if_needed(); loc.hover(); pg.wait_for_timeout(900)
            ov = pg.locator(".v-overlay--active .v-overlay__content:visible")
            out[lab] = "no tooltip" if ov.count() == 0 else {"img": ov.last.locator("img").count(), "text": ov.last.inner_text()[:80]}
            pg.mouse.move(5, 5); pg.wait_for_timeout(400)
        except Exception as e:
            out[lab] = f"err {e!s:.60}"
    b.close()
print(json.dumps(out, indent=1, ensure_ascii=False))
json.dump(out, open("/workspace/fansim/qa_tooltips/data/headless_hover2.json", "w"), indent=1, ensure_ascii=False)
