"""Write the real text of the web page from stats.json, so every number on the site matches the data.

For every city in web/data/<city>/stats.json it writes:
  - web/data/<city>/panel.html  the panel (headline, stacked bar, zones, proposals) in Spanish + English
  - web/data/cities.json        the list of cities, for the city selector
And it copies the default city's panel straight into web/index.html (between the BEGIN/END
markers), so the figures are readable WITHOUT JavaScript: by people, search engines and the
AI judging system.

Usage:  python pipeline/render_html.py      (run it after build.py)
"""
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
DEFAULT_CITY = "culiacan"

# Map colors (keep in sync with RAMP in web/app.js). A one-hue ordinal ramp, light = closer,
# checked with the dataviz validator: monotone lightness, visible steps, light end >= 2:1.
RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]
INK = ["#0b0b0b", "#0b0b0b", "#ffffff", "#ffffff", "#ffffff"]  # readable text on each color
BAND_LABELS = {"le5": "≤5 min", "le10": "5–10 min", "le15": "10–15 min", "le20": "15–20 min", "gt20": ">20 min"}
TYPE = {  # proposal types
    "escuela": ("Escuela pública", "Public school"),
    "gobierno": ("Edificio de gobierno", "Government building"),
    "social": ("Centro comunitario", "Community center"),
    "deportivo": ("Unidad deportiva", "Sports center"),
}


DIRECTIONS = {"N": ("norte", "North"), "NE": ("noreste", "Northeast"), "E": ("este", "East"),
              "SE": ("sureste", "Southeast"), "S": ("sur", "South"), "SW": ("suroeste", "Southwest"),
              "W": ("oeste", "West"), "NW": ("noroeste", "Northwest")}


def zone_label(z):
    """Neighborhood names when Overture has them; otherwise direction and distance from downtown."""
    if z["name"]:
        return esc(z["name"])
    es, en = DIRECTIONS[z["dir"]]
    return both(f"Zona {es} · a {z['km']} km del centro", f"{en} area · {z['km']} km from downtown")


def esc(s):
    return html.escape(str(s), quote=True)


def num(x):
    return f"{round(x):,}"  # 17,039 - Mexico and English both use a comma for thousands


def pct(part, total):
    return f"{100 * part / total:.1f}%"


def both(es, en):
    """Same text in both languages; CSS shows the one that matches <html lang>."""
    return f'<span lang="es">{es}</span><span lang="en">{en}</span>'


def bar(bands, total, mode, hidden):
    """Stacked bar of older adults per walking-time band + a text legend (the accessible table)."""
    segs, items = [], []
    for i, (key, label) in enumerate(BAND_LABELS.items()):
        p60 = bands[key]["pop60"]
        share = 100 * p60 / total
        inside = f"{share:.0f}%" if share >= 9 else ""
        segs.append(f'<span class="seg" style="flex-grow:{share:.2f};background:{RAMP[i]};color:{INK[i]}" '
                    f'title="{label}: {num(p60)} ({share:.1f}%)">{inside}</span>')
        items.append(f'<li><i style="background:{RAMP[i]}"></i><span class="band">{label}</span>'
                     f'<b>{num(p60)}</b><span class="muted">{share:.1f}%</span></li>')
    caption = (both("Adultos mayores según los minutos a pie hasta el refugio más cercano",
                    "Older adults by walking minutes to the nearest refuge") if mode == "ref" else
               both("Adultos mayores según los minutos a pie hasta un refugio, farmacia o tienda",
                    "Older adults by walking minutes to a refuge, pharmacy or convenience store"))
    return (f'<figure class="bands" data-mode="{mode}"{" hidden" if hidden else ""}>'
            f'<figcaption>{caption}</figcaption>'
            f'<div class="bar" aria-hidden="true">{"".join(segs)}</div>'
            f'<ul class="legend">{"".join(items)}</ul></figure>')


def panel(s):
    """The city panel: everything in it comes from stats.json."""
    tot60 = s["population"]["pop60"]
    far = s["access_refugio"]["gt15"]["pop60"]
    far_any = s["access_any"]["gt15"]["pop60"]
    p = s["proposals"]
    out = [f'<div class="city-panel" data-city="{esc(s["id"])}">']

    # Headline
    out.append(
        f'<section class="summary"><p class="eyebrow">{esc(s["city"])}, {esc(s["state"])}</p>'
        f'<p class="hero"><strong class="hero-num">{num(far)}</strong> '
        + both("adultos mayores (60+) viven a más de 15 minutos a pie del refugio fresco más cercano.",
               "older adults (60+) live more than a 15-minute walk from the nearest cool refuge.")
        + '</p><p class="hero-sub">'
        + both(f"Con lugares de Overture Maps y población de Meta HRSL, son el {pct(far, tot60)} de los {num(tot60)} "
               f"adultos mayores de la ciudad. Si también cuentan las farmacias y tiendas de conveniencia, "
               f"quedan {num(far_any)} ({pct(far_any, tot60)}).",
               f"With places from Overture Maps and population from Meta HRSL, that is {pct(far, tot60)} of the city's {num(tot60)} "
               f"older adults. Counting pharmacies and convenience stores too, {num(far_any)} "
               f"({pct(far_any, tot60)}) remain that far.")
        + "</p>")
    out.append(bar(s["map_bands"]["refugio"], tot60, "ref", hidden=False))
    out.append(bar(s["map_bands"]["any"], tot60, "any", hidden=True))
    out.append("</section>")

    # Zones
    out.append('<section class="zones"><h2>'
               + both("Dónde faltan refugios", "Where refuges are missing") + "</h2><p class=\"muted\">"
               + both("Zonas con más adultos mayores a más de 15 min. Toca una para verla.",
                      "Areas with the most older adults more than 15 min away. Tap one to see it.")
               + "</p><ol>")
    for z in s["zones"][:5]:
        name = zone_label(z)
        out.append(f'<li><button type="button" class="fly" data-lon="{z["lon"]}" data-lat="{z["lat"]}" data-zoom="14.5">'
                   f'<span class="name">{name}</span><span class="meta">'
                   + both(f'{num(z["pop60"])} adultos mayores · mediana {z["median_min"]} min',
                          f'{num(z["pop60"])} older adults · median {z["median_min"]} min')
                   + "</span></button></li>")
    out.append("</ol></section>")

    # Proposals
    features = json.loads((WEB / "data" / s["id"] / "proposals.geojson").read_text())["features"]
    only_schools = all(f["properties"]["type"] == "escuela" for f in features)
    how_es = ("No se trata de cerrar escuelas: la idea es abrirlas como refugio en vacaciones de verano y fines de semana, "
              "cuando no hay clases, y solo las que tengan aire acondicionado." if only_schools else
              "No cambian de uso: la idea es abrirlos como refugio en las horas en que no se usan, y solo los que tengan "
              "aire acondicionado.")
    how_en = ("This doesn't mean closing schools: the idea is to open them as refuges during summer break and on weekends, "
              "when there are no classes, and only those with air conditioning." if only_schools else
              "Their use doesn't change: the idea is to open them as refuges when they're not in use, and only those "
              "with air conditioning.")
    out.append('<section class="proposals"><h2>'
               + both(f'{p["n"]} edificios públicos que podrían abrir como refugio',
                      f'{p["n"]} public buildings that could open as refuges')
               + '</h2><p class="muted">'
               + both(f'Hoy, el {p["pct60_le10_before"]}% de los adultos mayores de la ciudad tiene un refugio a 10 min o menos '
                      f'caminando. Con estos {p["n"]} sería el {p["pct60_le10_after"]}%: {num(p["new_pop60"])} personas más. '
                      + how_es,
                      f'Today, {p["pct60_le10_before"]}% of the city\'s older adults have a refuge within a 10-minute walk. '
                      f'With these {p["n"]} it would be {p["pct60_le10_after"]}%: {num(p["new_pop60"])} more people. '
                      + how_en)
               + "</p><ol>")
    for f in features:
        q = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        es_t, en_t = TYPE.get(q["type"], (q["type"], q["type"]))
        out.append(f'<li><button type="button" class="fly" data-lon="{lon}" data-lat="{lat}" data-zoom="15.5" '
                   f'data-rank="{q["rank"]}"><span class="rank">{q["rank"]}</span><span class="name">{esc(q["name"])}</span>'
                   f'<span class="meta">{both(es_t, en_t)} · '
                   + both(f'+{num(q["new_pop60"])} adultos mayores a ≤10 min',
                          f'+{num(q["new_pop60"])} older adults within 10 min')
                   + "</span></button></li>")
    out.append("</ol></section></div>")
    return "".join(out)


def meta(s):
    """<head> tags for search engines and link previews (English: the judges' language)."""
    far = num(s["access_refugio"]["gt15"]["pop60"])
    desc = (f"{far} older adults in {s['city']}, Mexico, live more than a 15-minute walk from the nearest "
            f"cool refuge. A walking-time map built from open data on AWS, with live walking routes from "
            f"Amazon Location Service.")
    return (f'<meta name="description" content="{esc(desc)}">\n'
            f'  <meta property="og:title" content="Refugio - how far is the nearest cool place, on foot, in {esc(s["city"])}?">\n'
            f'  <meta property="og:description" content="{esc(desc)}">\n'
            f'  <meta property="og:type" content="website">\n'
            f'  <meta property="og:image" content="{SITE}/og.png">\n'  # screenshot by docs/diagrams/capture.py
            f'  <meta property="og:image:alt" content="Map of Culiacán colored by walking minutes to the nearest cool refuge">\n'
            f'  <meta name="twitter:card" content="summary_large_image">')


# ----------------------------------------------------------------------------- about.html and llms.txt
# A plain, static write-up of the project for judges, search engines and the AI scoring system.
# English only (the judges' language). Every number comes from stats.json or docs/validation.md.

SITE = "https://main.d6r3007drgrwp.amplifyapp.com"
REPO = "https://github.com/Josegas/Refugio-mapa-de-refugios-contra-el-calor"
ARTICLE = None  # URL of the AWS Builder Center article (links are only shown when set)
VIDEO = None    # URL of the video demo

HEAT_FACTS = [  # (fact, source URL)
    ("Sinaloa ranked first in Mexico for heat-related illness cases in epidemiological week 32 of 2026 "
     "(20 cases, Mexico's Health Ministry).",
     "https://www.yucatan.com.mx/merida/2026/08/20/otro-caso-de-golpe-de-calor-en-yucatan-en-mexico-hay-4-nuevas-defunciones.html"),
    ("Mexico recorded at least 121 deaths from extreme temperatures between March and August 2026.",
     "https://www.unotv.com/clima/muertes-calor-mexico-2026/"),
    ("Culiacán reaches 45 °C in summer.",
     "https://www.luznoticias.mx/2026-07-10/sinaloa/como-sobrevivir-a-un-golpe-de-calor-en-culiacan-la-capital-de-sinaloa-registra-hasta-45-c-/296549"),
    ("About 31% of Culiacán's city buses had no air conditioning in 2024.",
     "https://www.luznoticias.mx/2024-07-13/sinaloa/culiacan-estas-son-las-rutas-donde-hay-menos-camiones-con-aire-acondicionado/211490"),
]


def zone_label_en(z):
    if z["name"]:
        return esc(z["name"])
    return f"{DIRECTIONS[z['dir']][1]} area, {z['km']} km from downtown"


def validation_metrics():
    """The aggregate numbers in docs/validation.md (written by evidence.py), keyed by their row label."""
    text = (ROOT / "docs" / "validation.md").read_text()
    rows = {}
    for line in text.splitlines():
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$", line)  # two-column table rows only
        if m:
            rows[m.group(1)] = m.group(2).replace("**", "")
    rows["sample"] = re.search(r"(\d+) random hexagons", text).group(1)
    needed = ["Median absolute difference", "90th percentile of the absolute difference", "Within ±2 min",
              "Within ±5 min", "Correlation", "Found by Amazon Location within 300 m",
              "...and with a compatible category",
              "Hexagons where Amazon Location knows a refuge-type place clearly closer",
              "Share of the sampled older adults living in those hexagons"]
    missing = [k for k in needed if k not in rows]
    if missing:
        raise SystemExit(f"docs/validation.md is missing rows: {missing}")
    return rows


def table(head, rows, cls=""):
    th = "".join(f"<th scope=\"col\">{h}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table{f" class={cls!r}" if cls else ""}><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'


FIGURES = {  # images from docs/assets/ shown on about.html (copied to web/img/ by main())
    "k1_architecture.png": "Architecture diagram: a data pipeline reads Overture Maps and Meta HRSL from Amazon S3 "
                           "and writes static files; GitHub Actions deploys them to AWS Amplify; the browser calls "
                           "Amazon Location Maps, Places and Routes.",
    "k8_validation_culiacan.png": "Scatter plot of walking minutes, open-data map versus Amazon Location routes, for "
                                  "50 random hexagons: the points sit on the y = x line.",
}


def figure(name, caption):
    if not (WEB / "img" / name).exists():
        return ""
    return (f'<figure><img src="img/{name}" alt="{esc(FIGURES[name])}" loading="lazy">'
            f'<figcaption>{caption}</figcaption></figure>')


def links_html():
    items = [f'<a href="./">Live map</a>', f'<a href="{REPO}">Source code (MIT)</a>']
    if ARTICLE:
        items.append(f'<a href="{ARTICLE}">Article on AWS Builder Center</a>')
    if VIDEO:
        items.append(f'<a href="{VIDEO}">Video demo</a>')
    return " · ".join(items)


def census_html(cities):
    """HRSL vs the 2020 census (written into stats.json by pipeline/census.py)."""
    if not all("census" in s for s in cities):
        return ""
    rows = [[esc(s["city"]), f'{s["census"]["share60_census_pct"]}%', f'{s["census"]["share60_hrsl_pct"]}%',
             f'{num(s["access_refugio"]["gt15"]["pop60"])} → about {num(s["census"]["gt15_pop60_if_census_share"])}']
            for s in cities]
    return ("<p><b>How many older adults? HRSL vs the 2020 census.</b> INEGI's census (ITER 2020) counts a larger "
            "share of people aged 60+ in each city than HRSL does in our study area. If HRSL misses older adults "
            "evenly, the shares on the map hold, but the counts are low:</p>"
            + table(["City", "Aged 60+, census 2020 (city)", "Aged 60+, HRSL", "Older adults more than 15 min away: "
                     "HRSL → with the census share"], rows))


def about_page(cities, v):
    """cities: list of stats dicts, Culiacán first. v: validation metrics."""
    c0 = cities[0]
    far0 = c0["access_refugio"]["gt15"]["pop60"]
    tot0 = c0["population"]["pop60"]
    p0 = c0["proposals"]
    desc = (f"{num(far0)} older adults in Culiacán, Mexico ({pct(far0, tot0)}) live more than a 15-minute walk "
            f"from the nearest cool refuge. How the Refugio map was built from open data on AWS and Amazon "
            f"Location Service, with results for Culiacán, Hermosillo and Mexicali.")
    out = [f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>About Refugio: walking time to a cool place for older adults in 45 °C heat</title>
  <meta name="description" content="{esc(desc)}">
  <meta property="og:title" content="About Refugio: walking time to a cool place in 45 °C heat">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:type" content="article">
  <meta property="og:image" content="{SITE}/og.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="about.css">
</head>
<body>
<!-- Generated by pipeline/render_html.py from web/data/*/stats.json and docs/validation.md. Do not edit by hand. -->
<main class="doc">
<p class="links">{links_html()}</p>
<h1>Refugio: how far do older adults have to walk in 45 °C heat to reach a cool place?</h1>
<p class="lede">In Culiacán, Mexico, <strong>{num(far0)} older adults (60+), {pct(far0, tot0)} of the
{num(tot0)} who live in the city, are more than a 15-minute walk from the nearest air-conditioned place
where they can stay without buying anything</strong>, according to open data (places from Overture Maps, population from Meta HRSL). Refugio maps
that walking time for every block-sized hexagon, shows where cool refuges are missing, ranks the
existing public buildings that could open as refuges, and gives anyone a live walking route from
their own address with Amazon Location Service.</p>

<h2>Key figures</h2>
"""]
    rows = []
    for s in cities:
        t60 = s["population"]["pop60"]
        far = s["access_refugio"]["gt15"]["pop60"]
        far_any = s["access_any"]["gt15"]["pop60"]
        p = s["proposals"]
        rows.append([f'{esc(s["city"])}, {esc(s["state"])}', num(t60), f"{num(far)} ({pct(far, t60)})",
                     f"{num(far_any)} ({pct(far_any, t60)})",
                     f'{p["pct60_le10_before"]}% → {p["pct60_le10_after"]}%'])
    out.append(table(["City", "Older adults (60+)", "More than 15 min on foot from a refuge",
                      "More than 15 min, counting pharmacies and convenience stores too",
                      f"Within 10 min of a refuge: today → with {p0['n']} proposed public buildings"], rows))
    out.append(f"""<p class="note">Walking speed 3.6 km/h, along the real street network. Older adults are
people aged 60 or more in the Meta/CIESIN High Resolution Settlement Layer, which counts about 30% fewer of them
than Mexico's 2020 census (see the evidence below). A refuge is a mall, department
store, large supermarket, library, museum, cultural or community center (air conditioning assumed from the
type of place).</p>

<h2>The problem</h2>
<ul>
{"".join(f'<li>{esc(f)} <a href="{u}">Source</a>.</li>' for f, u in HEAT_FACTS)}
</ul>
<p>An older adult without a car walks to wherever they can cool down. A radius on a map says nothing about
how far that is on foot: rivers, highways and dead-end streets make the real walk longer. Refugio
measures the walk along the streets and counts who lives at each distance.</p>

<h2>What you can explore on the map</h2>
<ul>
<li><b>Walking-time hexagons.</b> Each H3 hexagon (about 1.5 ha) is colored by the minutes on foot to the
nearest refuge, in 5 bands: ≤5, 5–10, 10–15, 15–20 and more than 20 minutes. Lighter is closer.</li>
<li><b>Refuges only, or refuges plus quick stops.</b> A switch adds pharmacies and convenience stores, where
you can step in for a moment and buy water.</li>
<li><b>Where older adults live.</b> A filter hides hexagons with fewer than 10 older adults.</li>
<li><b>Where refuges are missing.</b> The areas with the most older adults more than 15 minutes away; tap one
to fly there.</li>
<li><b>Proposed refuges.</b> The {p0["n"]} existing public buildings that would bring the most older adults within
a 10-minute walk, numbered on the map.</li>
<li><b>From your home.</b> Type an address, tap the map or use your location. Amazon Location draws the area
you can reach on foot in 5, 10 and 15 minutes, the walking route to the nearest refuge, and the cool places
it knows nearby. Three example buttons start a search in the areas with the biggest gaps.</li>
<li><b>Three cities.</b> Culiacán (Sinaloa), Hermosillo (Sonora) and Mexicali (Baja California), built with
the same pipeline.</li>
</ul>

<h2>The data</h2>
""")
    out.append(table(["Dataset", "What it gives", "Version", "License"], [
        ['<a href="https://registry.opendata.aws/overture/">Overture Maps</a> places',
         "Points of interest with category, brand and confidence: the refuges, quick stops and candidate public buildings",
         f'Release {esc(c0["sources"]["overture_release"])}', "CDLA Permissive 2.0, Apache 2.0, CC0 (by source)"],
        ["Overture Maps transportation (segments)", "Streets and their connectors: the walking network",
         f'Release {esc(c0["sources"]["overture_release"])}', "ODbL, © OpenStreetMap contributors"],
        ["Overture Maps divisions", "City limits (Culiacán) and municipality and neighborhood names",
         f'Release {esc(c0["sources"]["overture_release"])}', "ODbL, © OpenStreetMap contributors"],
        ['<a href="https://registry.opendata.aws/dataforgood-fb-hrsl/">Meta HRSL</a> general and elderly 60+',
         "Total population and people aged 60+ at about 30 m resolution", "Latest (Cloud-Optimized GeoTIFF)",
         "CC BY 4.0, Meta and CIESIN – Columbia University"],
    ]))
    d = c0["network"]["detour_factor"]
    out.append("""<p>Both datasets are on the <a href="https://registry.opendata.aws/">Registry of Open Data on AWS</a>,
in Amazon S3. Only each city's bounding box is read, with HTTP range requests, so a city downloads in about
40 seconds instead of pulling global files.</p>

<h2>How it's put on the map</h2>
FIG_K1
<ol>
<li><b>Read from S3.</b> DuckDB queries the Overture GeoParquet files by bounding box; rasterio reads only the
needed window of the HRSL Cloud-Optimized GeoTIFFs.</li>
<li><b>Classify places.</b> Overture categories plus brand names decide what is a refuge, a quick stop, a
candidate public building or nothing. A documented exclusion list removes clear mistakes (banks labeled
as malls, a prison labeled as a government office).</li>
<li><b>Walking network.</b> Road segments are split at their connectors into a graph; motorways are left out.
In Culiacán, walking along the streets is a median DETOUR times the straight-line distance (5th-95th percentile:
DETOUR_RANGE), which is why a radius on a map underestimates the walk.</li>
<li><b>Population on H3.</b> HRSL pixels are summed into H3 resolution-10 hexagons inside the study area.</li>
<li><b>Walking minutes.</b> One multi-source Dijkstra run gives every hexagon the walk to the nearest refuge
door, at 3.6 km/h, a conservative speed for an older adult in the heat.</li>
<li><b>Proposals.</b> A greedy maximum-coverage algorithm picks, one at a time, the existing public building
(public schools, district offices, community and sports centers) that brings the most older adults
within 10 minutes.</li>
<li><b>Web.</b> The results are small static files (hexagons, refuges, proposals and statistics) drawn in the
browser with MapLibre GL JS and h3-js on an Amazon Location base map, and hosted on AWS Amplify.</li>
</ol>
<h3>Pipeline volumes, per city</h3>
""".replace("DETOUR_RANGE", f"{d['p5']} to {d['p95']}").replace("DETOUR", f"{d['median']}")
               .replace("FIG_K1", figure("k1_architecture.png", "A pipeline that runs once per city, and a static "
                                         "site that calls Amazon Location live. One AWS Region: us-west-2.")))
    vrows = []
    for s in cities:
        q, n = s["pipeline"], s["network"]
        cls = q["places_classified"]
        vrows.append([esc(s["city"]),
                      f'{num(q["places_read"])} → {num(cls["refugio"])} refuges, {num(cls["alivio"])} quick stops, '
                      f'{num(cls["candidates"])} candidates',
                      f'{num(q["segments_read"])} → {num(n["nodes"])} nodes, {num(n["edges"])} edges ({num(n["street_km"])} km)',
                      f'{num(q["populated_pixels"])} populated pixels → {num(s["counts"]["hexes"])} hexagons',
                      f'{num(cls["candidates"])} → {s["proposals"]["n"]}',
                      f'{q["fetch_seconds"]["total"]} s + {q["build_seconds"]} s' if q["fetch_seconds"] else f'{q["build_seconds"]} s'])
    out.append(table(["City", "Places read → classified", "Street segments → walking network",
                      "Population → hexagons", "Candidates → proposals", "Download + compute time"], vrows))
    out.append("""<p class="note">Times measured on a laptop on a home connection: the download reads from Amazon S3,
the compute step runs locally.</p>

<h2>AWS services</h2>
""")
    out.append(table(["Service", "Used for", "Why"], [
        ["Registry of Open Data on AWS (Amazon S3)", "Overture Maps and Meta HRSL, read by bounding box",
         "Open, global data in cloud-native formats: the same code works for any Mexican city."],
        ["Amazon Location Service: Maps", "Base map (vector style, API key)", "No tile server to run."],
        ["Amazon Location Service: Places", "Geocode (address search) and SearchNearby (cool places near you)",
         "Up-to-date commercial places that complement Overture. Used as SingleUse: results are never stored."],
        ["Amazon Location Service: Routes", "CalculateIsolines (5/10/15-minute walk) and CalculateRoutes (walking route)",
         "Pedestrian routing from the exact address, which can't be precomputed for every home."],
        ["AWS Amplify Hosting", "Static site with CDN and HTTPS", "Deployed by GitHub Actions with OIDC, no stored keys."],
        ["AWS Budgets", "Cost alerts", "Warns by email if the public API key is abused."],
    ]))
    out.append(f"""<p>The infrastructure (API keys restricted to this domain, Amplify app, budget and the GitHub deploy
role) is defined in Terraform. Every push to main runs the tests, a secret scan and Terraform checks before
deploying, and an uptime check runs every 3 hours.</p>

<h2>Evidence: is the open-data map right?</h2>
<p>For {v["sample"]} random hexagons where older adults live in Culiacán, Amazon Location <code>CalculateRoutes</code>
(Pedestrian, 3.6 km/h) walked from the hexagon to the refuge the map says is nearest:</p>
""")
    out.append(table(["Metric", "Value"], [
        ["Median absolute difference", esc(v["Median absolute difference"])],
        ["90th percentile of the difference", esc(v["90th percentile of the absolute difference"])],
        ["Within ±2 minutes", esc(v["Within ±2 min"])],
        ["Within ±5 minutes", esc(v["Within ±5 min"])],
        ["Correlation", esc(v["Correlation"])],
    ]))
    out.append(figure("k8_validation_culiacan.png", "Each dot is one hexagon: open-data minutes against Amazon "
                                                     "Location minutes. The shaded band is ±2 minutes."))
    out.append(f"""<p><b>What Overture is missing.</b> In {esc(v["Hexagons where Amazon Location knows a refuge-type place clearly closer"])}
of those hexagons (home to {esc(v["Share of the sampled older adults living in those hexagons"])} of the sampled older adults),
Amazon Location <code>SearchNearby</code> knows a refuge-type place at least 150 m closer. So the share of older
adults far from a refuge is probably somewhat lower than shown.</p>
<p><b>Spot-check.</b> Of 15 random refuges, Amazon Location found {esc(v["Found by Amazon Location within 300 m"])} by
name within 300 m, {esc(v["...and with a compatible category"])} with a compatible category.</p>
<p>Only these aggregate numbers were kept; the Amazon Location responses were not stored.</p>
{census_html(cities)}

<h2>Where refuges are missing</h2>
""")
    for s in cities:
        out.append(f'<h3>{esc(s["city"])}</h3>')
        out.append(table(["Area", "Older adults more than 15 min away", "Median walk"],
                         [[zone_label_en(z), num(z["pop60"]), f'{z["median_min"]} min'] for z in s["zones"][:5]]))
    out.append(f"<h2>{p0['n']} public buildings that could open as refuges in Culiacán</h2>")
    prows = []
    for f in json.loads((WEB / "data" / c0["id"] / "proposals.geojson").read_text())["features"]:
        q = f["properties"]
        prows.append([q["rank"], esc(q["name"]), TYPE.get(q["type"], ("", q["type"]))[1], f'+{num(q["new_pop60"])}'])
    out.append(table(["#", "Building", "Type", "Older adults newly within 10 min"], prows))
    out.append(f"""<p class="note">Today, {p0["pct60_le10_before"]}% of the city's older adults have a refuge within a 10-minute walk.
With these {p0["n"]} it would be {p0["pct60_le10_after"]}%: {num(p0["new_pop60"])} more people.
The algorithm only looks at where each building is; in all three cities the best-placed ones were public schools.
This doesn't mean closing schools: the idea is to open them as refuges during summer break and on weekends, when
there are no classes. Most public schools also teach an afternoon shift, so on school days other public buildings
would be needed. Each school would still need checking: air conditioning, staff, restrooms and the school's agreement. "Public" is inferred from the building's name, not from an official
registry.</p>

<h2>Limitations</h2>
<ul>
<li>Air conditioning and free entry are assumed from the type of place, not checked one by one.</li>
<li>Overture doesn't list every place (it has few convenience stores), so real access is probably better than shown.</li>
<li>HRSL counts about 30% fewer people aged 60+ than Mexico's 2020 census ({c0["census"]["share60_hrsl_pct"]}% vs
{c0["census"]["share60_census_pct"]}% in Culiacán), so the counts of older adults are probably low; the shares are not
affected if the gap is even across the city. See the evidence above.</li>
<li>Shade, sidewalks, safety and opening hours are not modeled: malls close at night, and the heat peaks from 2 to 5 pm.</li>
<li>The map doesn't know who has a car. The walking speed is an assumption; Amazon Location isolines use the
service's default pedestrian speed, which can't be set.</li>
<li>The natural next step is an official refuge network validated with the city.</li>
</ul>

<h2>Privacy</h2>
<p>No accounts, cookies or analytics. Addresses are never stored, and your location is only requested if
you press the button.</p>

<h2>Sources and licenses</h2>
<ul>
<li>Overture Maps Foundation, release {esc(c0["sources"]["overture_release"])}: transportation and divisions (ODbL,
© OpenStreetMap contributors); places (Meta and Microsoft, CDLA Permissive 2.0; Foursquare, Apache 2.0;
AllThePlaces, CC0).</li>
<li>Meta and CIESIN – Columbia University, High Resolution Settlement Layer (CC BY 4.0).</li>
<li>Base map: Amazon Location Service.</li>
<li>Code: MIT. Derived data in <code>web/data/</code>: ODbL. <a href="{REPO}">{REPO.replace("https://", "")}</a></li>
</ul>
<p class="links">{links_html()}</p>
</main>
</body>
</html>
""")
    return "\n".join(out)


def llms_txt(cities, v):
    """The same summary in plain text (https://llmstxt.org), for AI systems that read the site."""
    c0 = cities[0]
    lines = ["# Refugio", "",
             "> A walking-time map of cool refuges for older adults in 45 °C heat, in Culiacán, Hermosillo "
             "and Mexicali (Mexico). Built from open data on AWS (Overture Maps, Meta HRSL) and Amazon "
             "Location Service. Code: MIT.", "", "## Key figures", ""]
    for s in cities:
        t60, far, p = s["population"]["pop60"], s["access_refugio"]["gt15"]["pop60"], s["proposals"]
        lines.append(f"- {s['city']}: {num(far)} of {num(t60)} older adults (60+), {pct(far, t60)}, live more than "
                     f"a 15-minute walk from the nearest refuge. {p['n']} proposed public buildings would raise "
                     f"those within 10 minutes from {p['pct60_le10_before']}% to {p['pct60_le10_after']}%.")
    lines += ["", "## Evidence", "",
              f"- Against Amazon Location CalculateRoutes in {v['sample']} random Culiacán hexagons: median "
              f"difference {v['Median absolute difference']}, {v['Within ±2 min']} within ±2 minutes, "
              f"correlation {v['Correlation']}.",
              f"- Amazon Location knows a refuge-type place clearly closer in "
              f"{v['Hexagons where Amazon Location knows a refuge-type place clearly closer']} of those hexagons, "
              f"so the share of older adults far from a refuge is probably somewhat lower than shown.",
              f"- HRSL counts about 30% fewer people aged 60+ than INEGI's 2020 census ({c0['census']['share60_hrsl_pct']}% vs "
              f"{c0['census']['share60_census_pct']}% in Culiacán), so the counts of older adults are probably low: with the "
              f"census share, Culiacán's {num(c0['access_refugio']['gt15']['pop60'])} would be about "
              f"{num(c0['census']['gt15_pop60_if_census_share'])}.",
              "", "## Method", "",
              "- Overture places, streets and boundaries read by bounding box from Amazon S3 with DuckDB; "
              "HRSL population (total and 60+) from Cloud-Optimized GeoTIFFs with rasterio.",
              "- Walking network from Overture road segments, multi-source Dijkstra at 3.6 km/h, results on "
              "H3 resolution-10 hexagons.",
              "- Greedy maximum coverage over existing public buildings to propose new refuges.",
              "- Live layer: Amazon Location Geocode, SearchNearby, CalculateIsolines and CalculateRoutes "
              "from the user's address (results not stored).",
              "", "## Links", "",
              f"- [Live map]({SITE}/): the interactive map (Spanish by default, English button)",
              f"- [About]({SITE}/about.html): full write-up with tables",
              f"- [Source code]({REPO})"]
    if ARTICLE:
        lines.append(f"- [Article on AWS Builder Center]({ARTICLE})")
    if VIDEO:
        lines.append(f"- [Video demo]({VIDEO})")
    return "\n".join(lines) + "\n"


def replace_between(text, name, new):
    pattern = re.compile(rf"(<!-- BEGIN:{name} -->)(.*?)(<!-- END:{name} -->)", re.S)
    if not pattern.search(text):
        raise SystemExit(f"Marker <!-- BEGIN:{name} --> not found in index.html")
    return pattern.sub(lambda m: m.group(1) + "\n" + new + "\n" + m.group(3), text)


def main():
    cities = []
    for stats_file in sorted((WEB / "data").glob("*/stats.json")):
        s = json.loads(stats_file.read_text())
        (stats_file.parent / "panel.html").write_text(panel(s) + "\n")
        cities.append({k: s[k] for k in ("id", "city", "state", "center", "zoom")})
        print(f"wrote {stats_file.parent.relative_to(ROOT)}/panel.html")
    (WEB / "data" / "cities.json").write_text(json.dumps(cities, ensure_ascii=False, indent=1) + "\n")

    default = json.loads((WEB / "data" / DEFAULT_CITY / "stats.json").read_text())
    index = WEB / "index.html"
    text = index.read_text()
    text = replace_between(text, "meta", "  " + meta(default) + "\n  ")
    text = replace_between(text, "panel", panel(default))
    index.write_text(text)
    print(f"updated {index.relative_to(ROOT)} with {DEFAULT_CITY}")

    # Images for about.html: copied from docs/assets/ (drawn by docs/diagrams/render.py and evidence.py)
    (WEB / "img").mkdir(exist_ok=True)
    for name in FIGURES:
        src = ROOT / "docs" / "assets" / name
        if src.exists():
            shutil.copyfile(src, WEB / "img" / name)

    # about.html and llms.txt: all cities, default city first
    order = [c["id"] for c in cities]
    order.sort(key=lambda cid: cid != DEFAULT_CITY)
    all_stats = [json.loads((WEB / "data" / cid / "stats.json").read_text()) for cid in order]
    v = validation_metrics()
    (WEB / "about.html").write_text(about_page(all_stats, v))
    (WEB / "llms.txt").write_text(llms_txt(all_stats, v))
    print("wrote web/about.html and web/llms.txt")


if __name__ == "__main__":
    main()
