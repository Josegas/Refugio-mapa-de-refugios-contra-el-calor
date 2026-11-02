"""Screenshots, the demo GIF and the latency of one search, all taken from the LIVE site.

  K4  docs/assets/k4_hero.png, k4_search.png, k4_proposals.png, k4_mobile.png, k4_mobile_search.png
      web/og.png (1200x630, the link preview image)
  K5  docs/assets/k5_search.gif     type an address -> walking areas -> route
      docs/assets/latency.json      median time of each Amazon Location call (used by K3 in render.py)

Latency is measured in the browser around each fetch() to Amazon Location (like ?debug=1 does).
Only timings are kept; the responses are drawn on screen and discarded (IntendedUse "SingleUse").
Cost: about 6 billable requests per search, ~50 per full run (free tier: 10,000 routes a month).

Usage:  python docs/diagrams/capture.py [--no-latency]     (needs: pip install playwright pillow && playwright install chromium)
"""
import io
import json
import os
import statistics
import sys
from datetime import date
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs" / "assets"
SITE = "https://main.d6r3007drgrwp.amplifyapp.com"
DEMO_ADDRESS = "Colonia Libertad, Culiacán"  # biggest gap in Culiacán; nearest refuge is a public museum
LATENCY_QUERIES = ["Colonia Libertad, Culiacán", "Colonia Díaz Ordaz, Culiacán", "Colonia Guadalupe Victoria, Culiacán",
                   "Colonia Las Quintas, Culiacán", "Colonia Hidalgo, Culiacán"]
CALL_NAMES = {"/v2/geocode": "Geocode", "/v2/isolines": "CalculateIsolines", "/v2/routes": "CalculateRoutes",
              "/v2/search-nearby": "SearchNearby"}

# Runs in the page before the app: times every call to Amazon Location (*.geo.*.amazonaws.com)
TIMER = """
window.__calls = [];
const realFetch = window.fetch;
window.fetch = async (url, options) => {
  const start = performance.now();
  const response = await realFetch(url, options);
  const u = String(url);
  if (u.includes('.geo.')) window.__calls.push({ path: new URL(u).pathname, ms: performance.now() - start });
  return response;
};
"""


def open_page(browser, width, height, scale=2, lang="en"):
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
    page.add_init_script(TIMER)
    page.goto(f"{SITE}/?lang={lang}", wait_until="networkidle")
    wait_for_map(page)
    return page


def wait_for_map(page, extra_ms=1200):
    """Until the hexagons are on the map, the camera has stopped and the base-map tiles are loaded."""
    page.wait_for_function("typeof map !== 'undefined' && map.getLayer('hexes') && !map.isMoving() "
                           "&& map.areTilesLoaded()", timeout=30000)
    page.wait_for_timeout(extra_ms)


def search(page, address, frames=None):
    """Type an address, press Search and wait until the three live calls came back and were drawn."""
    page.evaluate("window.__calls = []")
    page.fill("#address", "")
    if frames is None:
        page.fill("#address", address)
    else:  # for the GIF: type it like a person, grabbing a frame every few letters
        for i, ch in enumerate(address):
            page.type("#address", ch)
            if i % 3 == 2:
                frames.append(grab(page))
    page.click("#search-form button[type=submit]")
    page.wait_for_function("window.__calls.length >= 4", timeout=30000)
    if frames is not None:  # the camera flies to the result: keep grabbing frames
        for _ in range(22):
            frames.append(grab(page))
            page.wait_for_timeout(120)
    wait_for_map(page, 1500)
    return page.evaluate("window.__calls")


def show_result(page):
    """Scroll the panel so the search result (nearest refuge and minutes) is in view."""
    page.evaluate("document.querySelector('#search-result').scrollIntoView({block: 'start'})")
    page.wait_for_timeout(500)


def grab(page):
    return Image.open(io.BytesIO(page.screenshot())).convert("RGB")


def measure_latency(browser):
    page = open_page(browser, 1440, 900, scale=1)
    runs = []
    for q in LATENCY_QUERIES:
        calls = search(page, q)
        runs.append({CALL_NAMES[c["path"]]: c["ms"] for c in calls if c["path"] in CALL_NAMES})
        print(f"  {q}: " + ", ".join(f"{k} {v:.0f} ms" for k, v in runs[-1].items()))
    page.close()
    med = {k: round(statistics.median(r[k] for r in runs)) for k in CALL_NAMES.values()}
    parallel = [max(r["CalculateIsolines"], r["CalculateRoutes"], r["SearchNearby"]) for r in runs]
    med["search_total"] = round(statistics.median(r["Geocode"] + p for r, p in zip(runs, parallel)))
    return {"measured": date.today().isoformat(), "runs": len(runs), "site": SITE, **med}


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    exe = os.environ.get("CHROMIUM")  # optional: path to an already-installed Chromium
    with sync_playwright() as p:
        # Software WebGL: without these flags headless Chromium leaves most of a phone-size map blank
        args = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
        browser = p.chromium.launch(executable_path=exe, args=args) if exe else p.chromium.launch(args=args)

        if "--no-latency" not in sys.argv:
            print("latency")
            lat = measure_latency(browser)
            (ASSETS / "latency.json").write_text(json.dumps(lat, indent=1) + "\n")
            print("  medians:", lat)

        print("desktop screenshots")
        page = open_page(browser, 1440, 900)
        page.wait_for_timeout(2500)  # the first page of a run paints late (cold cache); without this the map came out blank
        page.screenshot(path=str(ASSETS / "k4_hero.png"))
        search(page, DEMO_ADDRESS)
        show_result(page)
        page.screenshot(path=str(ASSETS / "k4_search.png"))
        page.close()

        page = open_page(browser, 1440, 900)
        page.evaluate("document.querySelector('#city-panel .proposals').scrollIntoView({block: 'start'})")
        page.wait_for_timeout(600)
        page.screenshot(path=str(ASSETS / "k4_proposals.png"))
        page.close()

        print("phone screenshots")
        page = open_page(browser, 390, 844, scale=3)
        page.screenshot(path=str(ASSETS / "k4_mobile.png"))
        search(page, DEMO_ADDRESS)
        show_result(page)
        page.screenshot(path=str(ASSETS / "k4_mobile_search.png"))
        page.close()

        print("link preview image")
        page = open_page(browser, 1200, 630, scale=1)
        page.screenshot(path=str(ROOT / "web" / "og.png"))
        page.close()

        print("GIF")
        page = open_page(browser, 1280, 800, scale=1)
        frames = [grab(page)] * 6  # hold the first view for a moment
        search(page, DEMO_ADDRESS, frames)
        show_result(page)
        frames += [grab(page)] * 16  # hold the result
        page.close()
        browser.close()

    small = [f.resize((960, 600), Image.LANCZOS).quantize(colors=128, method=Image.Quantize.MEDIANCUT) for f in frames]
    small[0].save(ASSETS / "k5_search.gif", save_all=True, append_images=small[1:], duration=140, loop=0,
                  optimize=True)
    size = (ASSETS / "k5_search.gif").stat().st_size / 1e6
    print(f"wrote docs/assets/k5_search.gif ({len(frames)} frames, {size:.1f} MB)")


if __name__ == "__main__":
    main()
