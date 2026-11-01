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
        + both(f"Según los datos abiertos de Overture Maps, son el {pct(far, tot60)} de los {num(tot60)} "
               f"adultos mayores de la ciudad. Si también cuentan las farmacias y tiendas de conveniencia, "
               f"quedan {num(far_any)} ({pct(far_any, tot60)}).",
               f"According to Overture Maps open data, that is {pct(far, tot60)} of the city's {num(tot60)} "
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
    out.append('<section class="proposals"><h2>'
               + both(f'{p["n"]} edificios públicos que podrían abrir como refugio',
                      f'{p["n"]} public buildings that could open as refuges')
               + '</h2><p class="muted">'
               + both(f'Con estos {p["n"]}, los adultos mayores con un refugio a 10 min o menos pasan del '
                      f'{p["pct60_le10_before"]}% al {p["pct60_le10_after"]}% (+{num(p["new_pop60"])} personas).',
                      f'With these {p["n"]}, older adults within a 10-minute walk of a refuge go from '
                      f'{p["pct60_le10_before"]}% to {p["pct60_le10_after"]}% (+{num(p["new_pop60"])} people).')
               + "</p><ol>")
    for f in json.loads((WEB / "data" / s["id"] / "proposals.geojson").read_text())["features"]:
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
            f'  <meta property="og:type" content="website">')


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


if __name__ == "__main__":
    main()
