"""Live cockpit UI capture for layout review (Playwright)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8082/"
VIEWPORT = {"width": 1440, "height": 900}

TABS = [
    ("fan", "Fan — CFD design"),
    ("propeller", "Propeller — instant BEMT design"),
    ("mixed", "Mixed-flow — drop-in impeller"),
    ("volute", "Volute — radial blower"),
    ("cror", "CROR — stacked rotors"),
]


def wait_ready(page, timeout_ms: int = 120_000) -> None:
    page.wait_for_selector("text=Fan — CFD design", timeout=timeout_ms)
    page.wait_for_timeout(2500)


def top_tabs(page):
    # Top-level VTabs are the first .v-tabs group
    return page.locator(".v-tabs").first.locator(".v-tab")


def click_top_tab(page, label: str) -> None:
    tab = top_tabs(page).filter(has_text=label)
    tab.first.click()
    page.wait_for_timeout(1500)


def click_fan_subtab(page, name: str) -> None:
    # Fan subtabs live in the right column's second .v-tabs
    tabs = page.locator(".v-tabs").nth(1).locator(".v-tab")
    tabs.filter(has_text=name).first.click()
    page.wait_for_timeout(1000)


def dump_visible_structure(page) -> dict:
    return page.evaluate(
        """() => {
          const isVis = el => !!(el && el.offsetParent !== null);
          const tabs = [...document.querySelectorAll('.v-tab')].filter(isVis).map(el => ({
            text: (el.innerText || '').trim().replace(/\\s+/g, ' '),
            selected: el.classList.contains('v-tab--selected') || el.getAttribute('aria-selected') === 'true',
          }));
          const buttons = [...document.querySelectorAll('button.v-btn')]
            .filter(isVis)
            .map(el => ({
              text: (el.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 90),
              disabled: el.disabled || el.classList.contains('v-btn--disabled'),
            }));
          const cards = [...document.querySelectorAll('.v-card')]
            .filter(isVis)
            .map(el => {
              const r = el.getBoundingClientRect();
              return {
                title: ((el.querySelector('.text-subtitle-2') || {}).innerText || '').trim().slice(0, 120),
                h: Math.round(r.height),
                top: Math.round(r.top),
                bottom: Math.round(r.bottom),
              };
            });
          const captions = [...document.querySelectorAll('.text-caption')]
            .filter(isVis)
            .map(el => (el.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 180))
            .filter(Boolean)
            .slice(0, 30);
          const selects = [...document.querySelectorAll('.v-select')]
            .filter(isVis)
            .map(el => ((el.querySelector('.v-label') || {}).innerText || '')
              .trim().replace(/\\s+/g, ' ').slice(0, 80));
          const switches = [...document.querySelectorAll('.v-switch')]
            .filter(isVis)
            .map(el => (el.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 120));
          const panels = [...document.querySelectorAll('.v-expansion-panel-title')]
            .filter(isVis)
            .map(el => (el.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 100));
          return {
            title: document.title,
            tabs, buttons, cards, captions, selects, switches, panels,
            scrollHeight: document.documentElement.scrollHeight,
            clientHeight: document.documentElement.clientHeight,
          };
        }"""
    )


def visible_button(page, text: str):
    btns = page.locator("button.v-btn")
    for i in range(btns.count()):
        b = btns.nth(i)
        try:
            if not b.is_visible():
                continue
            t = (b.inner_text() or "").strip()
            if text.lower() in t.lower():
                return b
        except Exception:
            continue
    return None


def safe_click_button(page, text: str) -> str:
    btn = visible_button(page, text)
    if btn is None:
        return f"missing_or_hidden:{text}"
    try:
        if btn.is_disabled():
            return f"disabled:{text}"
        btn.scroll_into_view_if_needed()
        btn.click(timeout=8000)
        return f"clicked:{text}"
    except Exception as exc:  # noqa: BLE001
        return f"click_failed:{text}:{str(exc)[:100]}"


def scroll_right_panel(page, dy: int = 600) -> None:
    page.evaluate(
        """(dy) => {
          const cards = [...document.querySelectorAll('.v-card')].filter(el => el.offsetParent);
          // Prefer scrolling the tall right-side column container
          const candidates = [...document.querySelectorAll('.v-col')].filter(el => el.offsetParent);
          let target = null;
          for (const c of candidates) {
            const r = c.getBoundingClientRect();
            if (r.left > 500 && r.height > 400) { target = c; break; }
          }
          if (target) target.scrollBy(0, dy);
          else window.scrollBy(0, dy);
        }""",
        dy,
    )
    page.wait_for_timeout(500)


def main() -> None:
    findings: dict = {"url": URL, "tabs": {}, "notes": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=VIEWPORT)
        page = context.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        wait_ready(page)
        page.screenshot(path=str(OUT / "00_landing_fan.png"), full_page=False)

        for key, label in TABS:
            click_top_tab(page, label)
            page.wait_for_timeout(2000)
            shot = OUT / f"{key}_viewport.png"
            page.screenshot(path=str(shot), full_page=False)
            full = OUT / f"{key}_full.png"
            page.screenshot(path=str(full), full_page=True)
            struct = dump_visible_structure(page)
            actions = []

            try:
                if key == "fan":
                    for sub in ("Design", "Results", "Library"):
                        click_fan_subtab(page, sub)
                        page.screenshot(path=str(OUT / f"fan_sub_{sub.lower()}.png"), full_page=False)
                        actions.append({"subtab": sub, "structure": dump_visible_structure(page)})
                    click_fan_subtab(page, "Design")
                    # scroll right column to reveal Assess/Optimize below fold
                    scroll_right_panel(page, 700)
                    page.screenshot(path=str(OUT / "fan_design_scrolled.png"), full_page=False)
                    actions.append({"scrolled_structure": dump_visible_structure(page)})
                    scroll_right_panel(page, 700)
                    page.screenshot(path=str(OUT / "fan_design_scrolled2.png"), full_page=False)
                    # expand first visible panel
                    panels = page.locator(".v-expansion-panel-title")
                    expanded = None
                    for i in range(panels.count()):
                        cand = panels.nth(i)
                        if cand.is_visible():
                            cand.scroll_into_view_if_needed()
                            cand.click(timeout=5000)
                            page.wait_for_timeout(500)
                            expanded = cand.inner_text()[:80]
                            break
                    actions.append({"expanded_panel": expanded or "none_visible"})
                    # scroll back up for Preview
                    scroll_right_panel(page, -1400)
                    actions.append({"preview": safe_click_button(page, "Preview geometry")})
                    page.wait_for_timeout(10000)
                    page.screenshot(path=str(OUT / "fan_after_preview.png"), full_page=False)
                    actions.append({"after_preview": dump_visible_structure(page)["captions"][:12]})

                elif key == "propeller":
                    actions.append({"analyze": safe_click_button(page, "Analyze (BEMT)")})
                    page.wait_for_timeout(6000)
                    page.screenshot(path=str(OUT / "propeller_after_analyze.png"), full_page=False)
                    actions.append({"structure_after": dump_visible_structure(page)})
                    # do NOT start Optimize (still multi-trial) or CFD refine

                elif key == "mixed":
                    actions.append({"preview": safe_click_button(page, "Preview")})
                    page.wait_for_timeout(10000)
                    page.screenshot(path=str(OUT / "mixed_after_preview.png"), full_page=False)
                    actions.append({"structure_after": dump_visible_structure(page)})

                elif key == "volute":
                    actions.append({"preview": safe_click_button(page, "Preview")})
                    page.wait_for_timeout(12000)
                    page.screenshot(path=str(OUT / "volute_after_preview.png"), full_page=False)
                    actions.append({"structure_after": dump_visible_structure(page)})

                elif key == "cror":
                    actions.append({"thin": safe_click_button(page, "Thin default")})
                    page.wait_for_timeout(10000)
                    page.screenshot(path=str(OUT / "cror_after_thin.png"), full_page=False)
                    actions.append({"structure_after": dump_visible_structure(page)})
            except Exception as exc:  # noqa: BLE001
                actions.append({"error": str(exc)[:300]})
                page.screenshot(path=str(OUT / f"{key}_error.png"), full_page=False)

            findings["tabs"][key] = {
                "label": label,
                "screenshot": str(shot),
                "full_screenshot": str(full),
                "structure": struct,
                "actions": actions,
            }

        (OUT / "findings.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")
        browser.close()
    print(f"Wrote findings to {OUT / 'findings.json'}")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"elapsed_s={time.time() - t0:.1f}")
