"""Draw the diagrams of the write-up as SVG, then export each one to PNG at 2x.

  K1  docs/assets/k1_architecture.svg/.png   architecture, with the official AWS Architecture Icons
  K2  docs/assets/k2_pipeline.svg/.png       pipeline funnel: how much data goes in and comes out of each stage
  K3  docs/assets/k3_search.svg/.png         sequence of one personal search, with measured latencies

Every number comes from web/data/culiacan/stats.json or docs/assets/latency.json (written by
docs/diagrams/capture.py), so the diagrams can be redrawn whenever the data changes.

The AWS icons are AWS trademarks, used as AWS allows for architecture diagrams. They are NOT in git
(they aren't covered by this repo's MIT license): the first run downloads the official icon package
into docs/diagrams/.icons/ (git-ignored).

Usage:  python docs/diagrams/render.py          (needs: pip install playwright && playwright install chromium)
"""
import base64
import json
import os
import textwrap
import urllib.request
import zipfile
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs" / "assets"
ICONS = Path(__file__).resolve().parent / ".icons"
ICON_PACKAGE = ("https://d1.awsstatic.com/onedam/marketing-channels/website/public/shared/architecture-icon-release/"
                "Icon-package_07312026.5846e92413caa21490223536cc97f1269e44fa92.zip")  # from aws.amazon.com/architecture/icons
WANTED = {  # short name -> file name inside the official package
    "s3": "Arch_Amazon-Simple-Storage-Service_64.svg",
    "location": "Arch_Amazon-Location-Service_64.svg",
    "amplify": "Arch_AWS-Amplify_64.svg",
    "budgets": "Arch_AWS-Budgets_64.svg",
    "iam": "Arch_AWS-Identity-and-Access-Management_64.svg",
    "glue": "Arch_AWS-Glue_64.svg",
    "athena": "Arch_Amazon-Athena_64.svg",
    "cloud": "AWS-Cloud-logo_32.svg",
    "client": "Res_Client_48_Light.svg",
    "users": "Res_Users_48_Light.svg",
    "gear": "Res_Gear_48_Light.svg",
    "docs": "Res_Documents_48_Light.svg",
}

# Colors: AWS "squid ink" for text and step badges, the map's blues for data, AWS category colors for groups
INK, INK2, MUTED, LINE = "#232f3e", "#4b5563", "#6b7280", "#d5dbdb"
BLUE, BLUE_LIGHT = "#1c5cab", "#eaf2fc"
GREEN, RED = "#7aa116", "#dd344c"  # AWS: storage & cost (green), front-end web & mobile / security (red)
PURPLE = "#8c4fff"  # AWS: analytics
FONT = "Noto Sans, Arial, Helvetica, sans-serif"


# ----------------------------------------------------------------------------- icons

def ensure_icons():
    """Download the official AWS icon package once and keep only the icons we use."""
    if all((ICONS / f).exists() for f in WANTED.values()):
        return
    ICONS.mkdir(parents=True, exist_ok=True)
    zpath = ICONS / "package.zip"
    if not zpath.exists():
        print("downloading the AWS Architecture Icons package (14 MB, once)")
        urllib.request.urlretrieve(ICON_PACKAGE, zpath)
    with zipfile.ZipFile(zpath) as z:
        for name in z.namelist():
            base = name.rsplit("/", 1)[-1]
            if "__MACOSX" not in name and base in WANTED.values():
                (ICONS / base).write_bytes(z.read(name))
    zpath.unlink()


def icon(name, x, y, size=48):
    data = base64.b64encode((ICONS / WANTED[name]).read_bytes()).decode()
    return f'<image x="{x}" y="{y}" width="{size}" height="{size}" href="data:image/svg+xml;base64,{data}"/>'


# ----------------------------------------------------------------------------- SVG helpers

def text(x, y, s, size=15, weight=400, color=INK, anchor="start", width=None, lh=1.35, italic=False):
    """Text, wrapped to `width` characters if given. Returns the SVG and the y below the last line."""
    lines = textwrap.wrap(s, width) if width else [s]
    style = ' font-style="italic"' if italic else ""
    spans = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else size * lh}">{escape(t)}</tspan>' for i, t in enumerate(lines))
    svg = (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
           f'fill="{color}" text-anchor="{anchor}"{style}>{spans}</text>')
    return svg, y + size * lh * len(lines)


def vcenter(x, ymid, s, size=15, weight=400, color=INK, width=None, lh=1.35):
    """Text wrapped to `width` characters and centered vertically on ymid."""
    n = len(textwrap.wrap(s, width)) if width else 1
    return text(x, ymid - (n - 1) * size * lh / 2 + size * 0.35, s, size, weight, color, width=width, lh=lh)[0]


def box(x, y, w, h, stroke=LINE, fill="#ffffff", dash=False, r=8, sw=1.5):
    d = ' stroke-dasharray="6 5"' if dash else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def badge(n, cx, cy, r=14):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{INK}"/>'
            f'<text x="{cx}" y="{cy + 5}" font-family="{FONT}" font-size="15" font-weight="700" fill="#fff" '
            f'text-anchor="middle">{n}</text>')


def arrow(points, color=INK, both=False, dash=False):
    pts = " ".join(f"{x},{y}" for x, y in points)
    d = ' stroke-dasharray="6 5"' if dash else ""
    start = ' marker-start="url(#head-start)"' if both else ""
    return (f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.2"{d}{start} '
            f'marker-end="url(#head)"/>')


def svg_doc(w, h, body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
  <marker id="head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
    <path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>
  <marker id="head-start" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="8" markerHeight="8" orient="auto">
    <path d="M10,0 L0,5 L10,10 z" fill="{INK}"/></marker>
</defs>
<rect width="{w}" height="{h}" fill="#ffffff"/>
{body}
</svg>
"""


def num(x):
    return f"{round(x):,}"


# ----------------------------------------------------------------------------- K1 architecture

def architecture(s):
    q = s["pipeline"]
    out = []
    t, _ = text(40, 52, "Refugio: architecture", 28, 700)
    out.append(t)
    t, _ = text(40, 82, "A data pipeline that runs once per city, a static web app that calls Amazon Location "
                        "Service live, and the results as an Apache Iceberg table for SQL. One AWS Region: us-west-2.",
                16, 400, INK2)
    out.append(t)

    # The two zones
    out.append(box(30, 110, 760, 760, stroke="#9aa5b1", fill="#fbfbfa", dash=True, r=12))
    out.append(box(820, 110, 750, 760, stroke="#9aa5b1", fill="#fbfbfa", dash=True, r=12))
    out.append(text(50, 140, "DATA PIPELINE (BUILD TIME)", 14, 700, MUTED)[0])
    out.append(text(840, 140, "LIVE APP (IN THE BROWSER)", 14, 700, MUTED)[0])

    # A1: open data on S3
    out.append(box(60, 160, 700, 180, stroke=GREEN, sw=2))
    out.append(icon("s3", 80, 178, 52))
    out.append(text(146, 198, "Registry of Open Data on AWS", 18, 700)[0])
    out.append(text(146, 222, "Amazon S3, public buckets, no account needed", 14, 400, INK2)[0])
    for i, (title, lines) in enumerate([
            ("Overture Maps", f"GeoParquet: places, road segments and boundaries. Release {s['sources']['overture_release']}."),
            ("Meta HRSL", "Cloud-Optimized GeoTIFF: total and 60+ population at about 30 m.")]):
        x = 80 + i * 340
        out.append(box(x, 246, 320, 78, stroke=LINE, fill=BLUE_LIGHT, r=6))
        out.append(text(x + 14, 270, title, 15, 700, BLUE)[0])
        out.append(text(x + 14, 292, lines, 13, 400, INK, width=44)[0])

    # 1: read by bounding box
    out.append(arrow([(410, 340), (410, 418)]))
    out.append(badge(1, 410, 378))
    out.append(text(436, 374, "Read only the city's bounding box", 14, 700)[0])
    out.append(text(436, 394, f"DuckDB + rasterio, HTTP range requests, {q['fetch_seconds']['total']:.0f} s", 13, 400, INK2)[0])

    # A2: the pipeline
    out.append(box(60, 420, 700, 190))
    out.append(icon("gear", 80, 438, 48))
    out.append(text(146, 458, "Python pipeline", 18, 700)[0])
    out.append(text(146, 482, f"Runs on a laptop: {q['build_seconds']:.1f} s of compute per city", 14, 400, INK2)[0])
    steps = ["Classify places", "Walking network", "Dijkstra, 3.6 km/h", "H3 hexagons", "Greedy coverage"]
    sx = 80
    for i, st in enumerate(steps):
        w = 118
        out.append(box(sx, 510, w, 74, stroke=LINE, fill=BLUE_LIGHT, r=6))
        out.append(text(sx + w / 2, 540, st, 13, 600, BLUE, anchor="middle", width=12)[0])
        if i < len(steps) - 1:
            out.append(arrow([(sx + w + 2, 547), (sx + w + 16, 547)]))
        sx += w + 18

    # 2: static files into the repo
    out.append(arrow([(410, 610), (410, 688)]))
    out.append(badge(2, 410, 648))
    out.append(text(436, 644, "Small static files + page text", 14, 700)[0])
    out.append(text(436, 664, f"{num(s['counts']['hexes'])} hexagons, refuges, proposals, stats.json", 13, 400, INK2)[0])

    # A3: repo + CI/CD
    out.append(box(60, 690, 700, 150))
    out.append(icon("docs", 80, 708, 48))
    out.append(text(146, 728, "Git repository and CI/CD", 18, 700)[0])
    out.append(text(146, 752, "Every push runs the tests, a secret scan and Terraform checks; only then it deploys.",
                    14, 400, INK2, width=62)[0])
    out.append(icon("iam", 146, 782, 40))
    out.append(text(196, 798, "Short-lived IAM role through OIDC:", 14, 600)[0])
    out.append(text(196, 818, "no AWS keys stored anywhere", 14, 400, INK2)[0])

    # 3: deploy to Amplify
    out.append(arrow([(760, 765), (868, 765)]))
    out.append(badge(3, 800, 765))
    out.append(text(815, 742, "Deploy", 13, 700, anchor="start")[0])

    # B1: Amplify
    out.append(box(870, 690, 330, 150, stroke=RED, sw=2))
    out.append(icon("amplify", 890, 708, 52))
    out.append(text(956, 730, "AWS Amplify Hosting", 18, 700)[0])
    out.append(text(956, 754, "Static site, CDN and HTTPS", 14, 400, INK2)[0])
    out.append(text(890, 792, "Figures are in the HTML, so the page reads without JavaScript.", 13, 400, INK2, width=40)[0])

    # B4: Budgets
    out.append(box(1230, 690, 310, 150, stroke=GREEN, sw=2))
    out.append(icon("budgets", 1250, 708, 52))
    out.append(text(1316, 730, "AWS Budgets", 18, 700)[0])
    out.append(text(1316, 754, "Cost alerts by email", 14, 400, INK2)[0])
    out.append(text(1250, 792, "Warns if someone abuses the public API key.", 13, 400, INK2, width=38)[0])

    # 4: Amplify serves the browser
    out.append(arrow([(1035, 690), (1035, 612)]))
    out.append(badge(4, 1035, 652))
    out.append(text(1060, 656, "HTML, JavaScript and data files", 14, 700)[0])

    # B2: the browser
    out.append(box(870, 420, 670, 190))
    out.append(icon("users", 890, 438, 52))
    out.append(text(956, 458, "Browser: residents, families, city planners", 18, 700)[0])
    out.append(text(956, 482, "MapLibre GL JS + h3-js draw the hexagons, refuges and proposals.", 14, 400, INK2)[0])
    out.append(text(956, 504, "Personal search: type an address, tap the map or use your location.", 14, 400, INK2)[0])
    out.append(text(890, 548, "Only the person's search goes to Amazon Location. No accounts, cookies or analytics; "
                              "addresses are never stored.", 13, 400, MUTED, width=90)[0])

    # B3: Amazon Location Service
    out.append(box(870, 160, 670, 196, stroke=RED, sw=2))
    out.append(icon("location", 890, 178, 52))
    out.append(text(956, 198, "Amazon Location Service", 18, 700)[0])
    out.append(text(956, 222, "API key restricted to the site's domain. Results used once (SingleUse), never stored.",
                    14, 400, INK2)[0])
    cards = [(5, "Maps", "Base map style and tiles"),
             (6, "Places", "Geocode: address to point. SearchNearby: cool places within 1.5 km"),
             (7, "Routes", "CalculateIsolines: 5/10/15-min walk. CalculateRoutes: route to the refuge")]
    for i, (n, title, desc) in enumerate(cards):
        x = 890 + i * 214
        out.append(box(x, 246, 200, 96, stroke=LINE, fill=BLUE_LIGHT, r=6))
        out.append(badge(n, x + 20, 268, 12))
        out.append(text(x + 40, 273, title, 15, 700, BLUE)[0])
        out.append(text(x + 12, 296, desc, 12, 400, INK, width=33, lh=1.3)[0])

    # 5-7: browser <-> Amazon Location
    out.append(arrow([(1205, 418), (1205, 358)], both=True))
    out.append(text(1222, 394, "HTTPS + API key", 14, 700)[0])

    # C: analytics, the results as an Apache Iceberg table (the live app doesn't use it)
    out.append(box(30, 905, 1540, 170, stroke="#9aa5b1", fill="#fbfbfa", dash=True, r=12))
    out.append(text(50, 935, "ANALYTICS (SQL OVER THE RESULTS)", 14, 700, MUTED)[0])
    out.append(box(60, 955, 1480, 100, stroke=PURPLE, sw=2))
    parts = [("s3", 80, "Apache Iceberg table on Amazon S3", "Private bucket. One snapshot per city: earlier versions can still be queried."),
             ("glue", 610, "AWS Glue Data Catalog", "Where the table and its columns are registered."),
             ("athena", 1040, "Amazon Athena", "SQL with no servers. Queries over 1 GB are cancelled.")]
    for name, x, title, desc in parts:
        out.append(icon(name, x, 978, 52))
        out.append(text(x + 66, 998, title, 17, 700)[0])
        out.append(text(x + 66, 1021, desc, 13, 400, INK2, width=50)[0])
    out.append(arrow([(1036, 1004), (1010, 1004)]))  # Athena -> Glue -> S3: the query path
    out.append(arrow([(606, 1004), (580, 1004)]))

    # 8: the same results into the Iceberg table
    out.append(arrow([(410, 840), (410, 953)]))
    out.append(badge(8, 410, 888))
    out.append(text(436, 893, "pipeline/iceberg.py: one commit per city", 14, 700)[0])

    # Legend
    legend = [
        "1  The pipeline reads only each city's bounding box from the open-data buckets on Amazon S3.",
        "2  It writes small static files, plus the page text with every figure, generated from stats.json.",
        "3  GitHub Actions tests the code and deploys it to AWS Amplify with a short-lived IAM role (OIDC).",
        "4  Amplify serves the site over a CDN with HTTPS.",
        "5  Amazon Location Maps draws the base map.",
        "6  Places geocodes the person's address and finds cool places nearby.",
        "7  Routes draws the area reachable on foot and the walking route to the nearest refuge.",
        "8  The same results go into an Apache Iceberg table on Amazon S3, one snapshot (commit) per city.",
        "9  Amazon Athena answers SQL over that table through the AWS Glue Data Catalog.",
    ]
    out.append(text(40, 1115, "How it flows", 16, 700)[0])
    for i, line in enumerate(legend):
        col, row = divmod(i, 5)
        n, desc = line.split("  ", 1)
        x, y = 40 + col * 790, 1142 + row * 26
        out.append(badge(n, x + 11, y - 5, 11))
        out.append(text(x + 30, y, desc, 13.5, 400, INK2)[0])
    return svg_doc(1600, 1280, "\n".join(out))


# ----------------------------------------------------------------------------- K2 pipeline funnel

def pipeline(s):
    q, n, c = s["pipeline"], s["network"], s["pipeline"]["places_classified"]
    out = []
    out.append(text(40, 52, f"Refugio: the data pipeline for {s['city']}", 28, 700)[0])
    out.append(text(40, 82, f"Downloaded from Amazon S3 in {q['fetch_seconds']['total']:.0f} s, computed in "
                            f"{q['build_seconds']:.1f} s on a laptop. Every number is from stats.json.", 16, 400, INK2)[0])
    rows = [
        ("Places", "Overture Maps places", f"{num(q['places_read'])} places in the bounding box",
         "Classify by category and brand; drop closed, low-confidence and known mistakes",
         f"{num(c['refugio'])} refuges, {num(c['alivio'])} quick stops, {num(c['candidates'])} candidate public buildings",
         f"{q['fetch_seconds']['places']:.0f} s"),
        ("Streets", "Overture Maps road segments", f"{num(q['segments_read'])} segments",
         "Split at connectors into a walking graph; no motorways",
         f"{num(n['nodes'])} intersections, {num(n['edges'])} street edges, {num(n['street_km'])} km",
         f"{q['fetch_seconds']['segments']:.0f} s"),
        ("People", "Meta HRSL, total and 60+", f"{num(q['populated_pixels'])} populated 30 m pixels",
         f"Sum into H3 hexagons inside the city ({s['study_area']['km2']} km²)",
         f"{num(s['counts']['hexes'])} hexagons, {num(s['population']['total'])} people, "
         f"{num(s['population']['pop60'])} aged 60+", f"{q['fetch_seconds']['population']:.0f} s"),
        ("Walk", "Graph + refuges + hexagons", f"{num(c['refugio'])} refuges as sources",
         "One multi-source Dijkstra at 3.6 km/h, door to door",
         f"Walking minutes for every hexagon: {num(s['access_refugio']['gt15']['pop60'])} older adults "
         f"more than 15 min away", None),
        ("Propose", "Candidate public buildings", f"{num(c['candidates'])} candidates",
         "Greedy maximum coverage, 10-minute walk, weighted by older adults",
         f"{s['proposals']['n']} proposals: {s['proposals']['pct60_le10_before']}% → "
         f"{s['proposals']['pct60_le10_after']}% of older adults within 10 min", None),
    ]
    heads = [("STAGE", 40), ("IN", 190), ("STEP", 560), ("OUT", 1010)]
    for h, x in heads:
        out.append(text(x, 130, h, 13, 700, MUTED)[0])
    y = 148
    for stage, src, inn, step, res, secs in rows:
        out.append(box(30, y, 1540, 104, stroke=LINE, fill="#fbfbfa", r=10))
        out.append(text(48, y + 46, stage, 20, 700, INK)[0])
        if secs:
            out.append(text(48, y + 72, f"download {secs}", 13, 400, MUTED)[0])
        out.append(box(190, y + 16, 330, 72, stroke=LINE, fill="#ffffff", r=6))
        out.append(text(206, y + 42, src, 13, 600, MUTED)[0])
        out.append(text(206, y + 66, inn, 16, 700, INK)[0])
        out.append(arrow([(522, y + 52), (556, y + 52)]))
        out.append(vcenter(574, y + 52, step, 14, 400, INK2, width=54))
        out.append(arrow([(972, y + 52), (1006, y + 52)]))
        out.append(box(1010, y + 16, 540, 72, stroke=BLUE, fill=BLUE_LIGHT, r=6))
        out.append(vcenter(1026, y + 52, res, 15, 700, BLUE, width=62))
        y += 118
    out.append(text(40, y + 22, "Output: hex.json, refuges.geojson, proposals.geojson and stats.json, served as static "
                                "files by AWS Amplify. Sources: Overture Maps Foundation, Meta and CIESIN HRSL.",
                    13.5, 400, MUTED)[0])
    return svg_doc(1600, y + 48, "\n".join(out))


# ----------------------------------------------------------------------------- K3 one search

def search_sequence(lat):
    """Sequence of one personal search. `lat`: measured latencies in ms (docs/assets/latency.json)."""
    out = []
    out.append(text(40, 52, "Refugio: one personal search, step by step", 28, 700)[0])
    out.append(text(40, 82, f"Measured on the live site ({lat['measured']}, median of {lat['runs']} searches): "
                            f"{lat['search_total']} ms from Search to the answer. The three calls after Geocode run in "
                            "parallel, so they take as long as the slowest one.", 16, 400, INK2)[0])
    lanes = [("Person", "users", 130), ("Browser (Refugio app)", "client", 470),
             ("Amazon Location Places", "location", 900), ("Amazon Location Routes", "location", 1330)]
    top, bottom = 120, 780
    for name, ic, x in lanes:
        out.append(icon(ic, x - 26, top, 52))
        out.append(text(x, top + 76, name, 15, 700, anchor="middle")[0])
        out.append(f'<line x1="{x}" y1="{top + 90}" x2="{x}" y2="{bottom}" stroke="{LINE}" stroke-width="2" stroke-dasharray="5 5"/>')
    P, B, PL, RT = (x for _, _, x in lanes)

    def msg(y, x1, x2, label, sub=None, dashed=False):
        parts = [arrow([(x1, y), (x2 - (8 if x2 > x1 else -8), y)], dash=dashed)]
        mid = (x1 + x2) / 2
        parts.append(text(mid, y - 10, label, 14, 600, anchor="middle")[0])
        if sub:  # white backing so a lifeline crossing behind it doesn't cut the text
            w = len(sub) * 7.6 + 14
            parts.append(f'<rect x="{mid - w / 2}" y="{y + 8}" width="{w}" height="20" fill="#ffffff"/>')
            parts.append(text(mid, y + 22, sub, 13, 400, MUTED, anchor="middle")[0])
        return "".join(parts)

    out.append(msg(250, P, B, "Types an address and presses Search"))
    out.append(msg(310, B, PL, "POST /v2/geocode", f"{lat['Geocode']} ms"))
    out.append(msg(370, PL, B, "Point [lon, lat]", dashed=True))
    # parallel block
    out.append(box(300, 410, 1180, 250, stroke=BLUE, fill="none", dash=True, r=10))
    out.append(text(316, 434, "In parallel", 14, 700, BLUE)[0])
    out.append(msg(470, B, RT, "POST /v2/isolines: 5, 10, 15 min on foot", f"{lat['CalculateIsolines']} ms"))
    out.append(msg(540, B, RT, "POST /v2/routes: to the nearest refuge (from the open-data map), 3.6 km/h",
                   f"{lat['CalculateRoutes']} ms"))
    out.append(msg(610, B, PL, "POST /v2/search-nearby: cool places within 1.5 km", f"{lat['SearchNearby']} ms"))
    out.append(msg(700, B, P, "Draws the 3 walking areas, the route and nearby places",
                   "Minutes from Amazon Location next to the open-data minutes", dashed=True))
    out.append(text(40, 830, "Per search: 6 billable requests (1 Geocode + 3 isolines + 1 route + 1 SearchNearby). "
                             "A tap on the map skips Geocode. Results are drawn and discarded, never stored.",
                    14, 400, INK2)[0])
    return svg_doc(1600, 860, "\n".join(out))


# ----------------------------------------------------------------------------- export

def to_png(svg_path, png_path):
    from playwright.sync_api import sync_playwright
    exe = os.environ.get("CHROMIUM")  # optional: path to an already-installed Chromium
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        svg = svg_path.read_text()
        w, h = (int(v) for v in svg.split('viewBox="0 0 ')[1].split('"')[0].split())
        page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
        page.goto(svg_path.resolve().as_uri())
        page.screenshot(path=str(png_path))
        browser.close()


def main():
    ensure_icons()
    ASSETS.mkdir(parents=True, exist_ok=True)
    s = json.loads((ROOT / "web" / "data" / "culiacan" / "stats.json").read_text())
    drawings = {"k1_architecture": architecture(s), "k2_pipeline": pipeline(s)}
    lat_file = ASSETS / "latency.json"
    if lat_file.exists():
        drawings["k3_search"] = search_sequence(json.loads(lat_file.read_text()))
    else:
        print("skipping K3: run docs/diagrams/capture.py first (it measures the latencies)")
    for name, svg in drawings.items():
        svg_path = ASSETS / f"{name}.svg"
        svg_path.write_text(svg)
        to_png(svg_path, ASSETS / f"{name}.png")
        print(f"wrote docs/assets/{name}.svg and .png")


if __name__ == "__main__":
    main()
