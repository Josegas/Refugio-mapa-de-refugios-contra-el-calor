"""How good is the HRSL 60+ layer? Compare it with Mexico's 2020 census (INEGI).

For each city, INEGI's "Principales resultados por localidad (ITER) 2020" gives the total population (POBTOT)
and the people aged 60 or more (P_60YMAS) of the city itself (the locality) and of the whole municipality.
We compare the census share of people aged 60+ with the share in our HRSL hexagons (stats.json).

If HRSL misses older adults evenly, the shares on the map (e.g. 31.4% more than 15 minutes away) don't
change, but the counts of older adults are low by the ratio census share / HRSL share.

Writes a section of docs/validation.md (between the census markers) and a "census" block in each stats.json.
Source: INEGI, Censo de Población y Vivienda 2020, ITER (open data, free use with attribution).

Usage:  python pipeline/census.py     (after build.py, which rewrites stats.json; then render_html.py)
"""
import csv
import io
import json
import re
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "census"
ITER = "https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/iter/iter_{state}_cpv2020_csv.zip"
CITIES = {  # city id -> (INEGI state code, municipality code, locality code of the city itself)
    "culiacan": ("25", "006", "0001"),
    "hermosillo": ("26", "030", "0001"),
    "mexicali": ("02", "002", "0001"),
}


def iter_rows(state):
    """The ITER table of one state (downloaded once into data/raw/census/, which is not in git)."""
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"iter_{state}.zip"
    if not path.exists():
        print(f"downloading INEGI ITER 2020 for state {state}")
        urllib.request.urlretrieve(ITER.format(state=state), path)
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if "conjunto_de_datos_iter" in n)
        yield from csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig"))


def main():
    rows_md = []
    for cid, (state, mun, loc) in CITIES.items():
        found = {}
        for r in iter_rows(state):
            if r["MUN"] == mun and r["LOC"] in ("0000", loc):
                found[r["LOC"]] = r
        city, municipality = found[loc], found["0000"]
        stats_file = ROOT / "web" / "data" / cid / "stats.json"
        s = json.loads(stats_file.read_text())
        hrsl_share = 100 * s["population"]["pop60"] / s["population"]["total"]
        census_share = 100 * int(city["P_60YMAS"]) / int(city["POBTOT"])
        ratio = census_share / hrsl_share
        far = s["access_refugio"]["gt15"]["pop60"]
        s["census"] = {
            "source": "INEGI, Censo de Población y Vivienda 2020, ITER",
            "locality": city["NOM_LOC"], "pobtot": int(city["POBTOT"]), "p_60ymas": int(city["P_60YMAS"]),
            "share60_census_pct": round(census_share, 1),
            "share60_census_municipality_pct": round(100 * int(municipality["P_60YMAS"]) / int(municipality["POBTOT"]), 1),
            "share60_hrsl_pct": round(hrsl_share, 1),
            "ratio": round(ratio, 2),
            "gt15_pop60_if_census_share": round(far * ratio, -2),  # rounded to hundreds: it's an estimate
        }
        stats_file.write_text(json.dumps(s, ensure_ascii=False, indent=1))
        c = s["census"]
        rows_md.append(f"| {s['city']} | {c['share60_census_pct']}% ({c['p_60ymas']:,} of {c['pobtot']:,}) | "
                       f"{c['share60_census_municipality_pct']}% | {c['share60_hrsl_pct']}% | {c['ratio']}× | "
                       f"{far:,} → about {int(c['gt15_pop60_if_census_share']):,} |")
        print(f"{cid}: census {c['share60_census_pct']}% vs HRSL {c['share60_hrsl_pct']}% (×{c['ratio']})")

    section = f"""<!-- BEGIN:census -->
## 4. People aged 60+: HRSL vs Mexico's 2020 census

Written by `pipeline/census.py` on {date.today().isoformat()}. Census: INEGI, *Censo de Población y Vivienda
2020, Principales resultados por localidad (ITER)*, columns `POBTOT` and `P_60YMAS`, for the city itself
(locality 0001) and for the whole municipality.

| City | Census 2020, city | Census 2020, municipality | HRSL, our study area | Census / HRSL | Older adults more than 15 min from a refuge: HRSL → if HRSL had the census share |
|---|---|---|---|---|---|
{chr(10).join(rows_md)}

HRSL counts about 30% fewer people aged 60+ than the census in all three cities. The **shares** on the map
(for example, 31.4% of older adults more than 15 minutes away) don't depend on that if HRSL misses older adults
evenly across each city; the **counts** of older adults are probably low by the ratio in the table. The map
keeps the HRSL figures, because they are the ones with a known location; the census-based figure is an estimate.

This pushes the other way from section 2. The places Overture is missing make the **share** of older adults far
from a refuge look higher than it is; the census says the **number** of older adults behind that share is higher.
<!-- END:census -->"""
    vpath = ROOT / "docs" / "validation.md"
    text = vpath.read_text()
    pattern = re.compile(r"<!-- BEGIN:census -->.*?<!-- END:census -->", re.S)
    if pattern.search(text):
        text = pattern.sub(lambda m: section, text)
    else:  # first run: insert before the manual notes
        text = text.replace("## Notes from the manual review", section + "\n\n## Notes from the manual review")
    vpath.write_text(text)
    print("wrote docs/validation.md (section 4) and the census block in each stats.json")


if __name__ == "__main__":
    main()
