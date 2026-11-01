"""Evidence for the write-up: how good is the open-data walking map?

Three checks against Amazon Location Service, with your own AWS credentials (profile "refugio"):

  1. Walking minutes. For N random hexagons where older adults live, CalculateRoutes (Pedestrian,
     3.6 km/h) from the hexagon's center to the refuge our map says is nearest. Compare with our minutes.
  2. Coverage gap. For the same hexagons, SearchNearby for refuge-type places (malls, department
     stores, libraries, museums, community centers). Does Amazon Location know one clearly closer
     (straight line) than our nearest refuge? This measures what Overture is missing.
  3. Spot-check. For K random refuges, SearchText for the refuge's name near its location: does
     Amazon Location know it within 300 m, and with a compatible category?

Only aggregate numbers are written (docs/validation.md) plus the K8 chart. The Amazon Location
responses themselves are never saved (IntendedUse "SingleUse").

Usage:  AWS_PROFILE=refugio python pipeline/evidence.py culiacan --n 50 --spot 15
Cost:   about 2*N + K billable requests.
"""
import argparse
import json
import re
import sys
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

import boto3
import h3
import numpy as np
from botocore.config import Config
from botocore.exceptions import ClientError
from pyproj import Geod

from build import norm

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "data"
DOCS = ROOT / "docs"
GEOD = Geod(ellps="WGS84")
SEED = 2026                       # fixed: anyone re-running the script gets the same sample
MIN_POP60 = 5                     # sample hexagons where older adults actually live
CLOSER_BY_M = 150                 # "clearly closer": at least this much nearer, so the same place
                                  # mapped at slightly different coordinates doesn't count as a gap
REFUGE_CATEGORIES = ["shopping_mall", "department_store", "library", "museum", "civic-community_center"]


def clients(region):
    session = boto3.Session(region_name=region)  # credentials from AWS_PROFILE (aws login)
    config = Config(retries={"total_max_attempts": 4, "mode": "adaptive"})
    return session.client("geo-routes", config=config), session.client("geo-places", config=config)


def walking_minutes(routes, origin, destination):
    """Amazon Location walking time in minutes at 3.6 km/h (only the number is kept)."""
    r = routes.calculate_routes(Origin=origin, Destination=destination, TravelMode="Pedestrian",
                                TravelModeOptions={"Pedestrian": {"Speed": 3.6}})
    legs = r["Routes"][0]["Legs"]
    seconds = sum(leg["PedestrianLegDetails"]["Summary"]["Overview"]["Duration"] for leg in legs)
    return seconds / 60


def nearest_refuge_type_place(places, origin, radius_m):
    """Distance (m) to the nearest refuge-type place Amazon Location knows within radius, or None."""
    if radius_m < 1:
        return None
    r = places.search_nearby(QueryPosition=origin, QueryRadius=int(radius_m), MaxResults=1,
                             Filter={"IncludeCategories": REFUGE_CATEGORIES})
    items = r.get("ResultItems", [])
    return items[0]["Distance"] if items else None


# Amazon Location category words that agree with each of our refuge types
COMPATIBLE = {
    "plaza": ("shopping_mall",), "departamental": ("department_store", "shopping_mall"),
    "super": ("grocery", "supermarket", "hypermarket", "warehouse", "department_store"),
    "biblioteca": ("library",), "museo": ("museum",), "cultura": ("cultur", "art", "museum"),
    "comunitario": ("community", "civic", "social", "government"),
}


def similar(a, b):
    a, b = norm(a), norm(b)
    return a in b or b in a or SequenceMatcher(None, a, b).ratio() >= 0.6


def check_refuge(places, position, name, kind):
    """Search the refuge by name near its location. Returns (exists, category_agrees): only yes/no is kept."""
    r = places.search_text(QueryText=name, BiasPosition=position, MaxResults=5, Language="es")
    for item in r.get("ResultItems", []):
        distance = GEOD.inv(position[0], position[1], item["Position"][0], item["Position"][1])[2]
        if distance <= 300 and similar(name, item.get("Title", "")):
            cats = " ".join(c.get("Id", "") for c in item.get("Categories", []))
            return True, any(word in cats for word in COMPATIBLE.get(kind, ()))
    return False, False


def load(city):
    hexes = json.loads((WEB / city / "hex.json").read_text())
    refuges = json.loads((WEB / city / "refuges.geojson").read_text())["features"]
    return hexes, refuges


def run_routes(city, n, region):
    """Checks 1 and 2: walking minutes and coverage gap, on the same random hexagons."""
    hexes, refuges = load(city)
    col = {name: i for i, name in enumerate(hexes["fields"])}
    rng = np.random.default_rng(SEED)
    candidates = [r for r in hexes["rows"] if r[col["pop60"]] >= MIN_POP60 and r[col["iref"]] >= 0]
    sample = [candidates[i] for i in rng.choice(len(candidates), n, replace=False)]
    routes, places = clients(region)

    ours, amazon, gaps, gap_pop60, calls = [], [], [], 0.0, 0
    for k, row in enumerate(sample, 1):
        lat, lon = h3.cell_to_latlng(row[col["h"]])
        origin = [lon, lat]
        refuge = refuges[row[col["iref"]]]["geometry"]["coordinates"]
        ours.append(row[col["ref"]])
        amazon.append(walking_minutes(routes, origin, refuge))
        straight = GEOD.inv(lon, lat, refuge[0], refuge[1])[2]
        closer = nearest_refuge_type_place(places, origin, straight - CLOSER_BY_M)
        gaps.append(closer is not None)
        if closer is not None:
            gap_pop60 += row[col["pop60"]]
        calls += 2
        print(f"  {k:2d}/{n}  ours {ours[-1]:5.1f} min  amazon {amazon[-1]:5.1f} min  "
              f"closer place known: {'yes' if closer is not None else 'no'}", flush=True)

    ours, amazon = np.array(ours), np.array(amazon)
    err = ours - amazon
    sample_pop60 = sum(r[col["pop60"]] for r in sample)
    return {
        "city": city, "date": date.today().isoformat(), "n": n, "seed": SEED, "calls": calls,
        "median_abs_err": float(np.median(np.abs(err))), "p90_abs_err": float(np.percentile(np.abs(err), 90)),
        "within_2": float(np.mean(np.abs(err) <= 2)), "within_5": float(np.mean(np.abs(err) <= 5)),
        "median_err": float(np.median(err)), "corr": float(np.corrcoef(ours, amazon)[0, 1]),
        "gap_share": float(np.mean(gaps)), "gap_pop60_share": gap_pop60 / sample_pop60,
        "ours": ours, "amazon": amazon,
    }


def run_spot(city, k, region):
    """Check 3: do K random refuges exist, and is their category the one we assumed?"""
    _, refuges = load(city)
    rng = np.random.default_rng(SEED + 1)
    pool = [f for f in refuges if f["properties"]["k"] == "refugio"]
    _, places = clients(region)
    rows = []
    for i in rng.choice(len(pool), k, replace=False):
        p, position = pool[i]["properties"], pool[i]["geometry"]["coordinates"]
        exists, agrees = check_refuge(places, position, p["n"], p["t"])
        rows.append((p["n"], p["t"], exists, agrees))
        print(f"  {p['n'][:40]:40s} {p['t']:14s} exists: {'yes' if exists else 'no '}  "
              f"category agrees: {'yes' if agrees else 'no'}", flush=True)
    return {"city": city, "date": date.today().isoformat(), "seed": SEED + 1, "calls": k, "rows": rows}


# ----------------------------------------------------------------------------- outputs

def chart(res, path):
    """K8: our minutes vs Amazon Location minutes, with y = x and a +-2 min band."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    top = max(res["ours"].max(), res["amazon"].max()) * 1.08
    fig, ax = plt.subplots(figsize=(6.4, 5.6), dpi=200)
    xs = np.array([0, top])
    ax.fill_between(xs, xs - 2, xs + 2, color="#e1e0d9", label="within ±2 min", zorder=1)
    ax.plot(xs, xs, color="#898781", linewidth=1, zorder=2, label="same time (y = x)")
    ax.scatter(res["amazon"], res["ours"], s=34, color="#2a78d6", edgecolor="#fcfcfb", linewidth=1.2,
               zorder=3, label=f"{res['n']} random hexagons")
    ax.set_xlim(0, top), ax.set_ylim(0, top)
    ax.set_xlabel("Amazon Location walking route (min, 3.6 km/h)", color="#52514e")
    ax.set_ylabel("Open-data map (min, 3.6 km/h)", color="#52514e")
    ax.set_title("Walking minutes to the nearest refuge: open-data map vs Amazon Location",
                 fontsize=10.5, loc="left", color="#0b0b0b")
    ax.grid(color="#e1e0d9", linewidth=0.6), ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
    ax.tick_params(colors="#52514e")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    fig.text(0.01, 0.01, f"Median absolute difference {res['median_abs_err']:.1f} min; "
             f"{100 * res['within_2']:.0f}% within ±2 min. Sources: Overture Maps, Meta HRSL, "
             f"Amazon Location Service ({res['date']}).", fontsize=7, color="#898781")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def pct(x):
    return f"{100 * x:.0f}%"


def report_routes(res, chart_path):
    return f"""## 1. Walking minutes: open-data map vs Amazon Location routes

{res['n']} random hexagons with at least {MIN_POP60} older adults (random seed {res['seed']}, run on {res['date']}).
For each one, Amazon Location `CalculateRoutes` (Pedestrian, 3.6 km/h) from the hexagon center to the
refuge our map says is nearest.

| Metric | Value |
|---|---|
| Median absolute difference | {res['median_abs_err']:.1f} min |
| 90th percentile of the absolute difference | {res['p90_abs_err']:.1f} min |
| Within ±2 min | {pct(res['within_2'])} |
| Within ±5 min | {pct(res['within_5'])} |
| Median difference (open data minus Amazon) | {res['median_err']:+.1f} min |
| Correlation | {res['corr']:.2f} |

A positive median difference means the open-data map is conservative: it measures to the nearest
street corner and then straight to the door, while Amazon Location routes to the address itself.

![Scatter plot of walking minutes, open-data map versus Amazon Location](assets/{chart_path.name})

## 2. Coverage gap: places Overture is missing

For the same hexagons, Amazon Location `SearchNearby` for refuge-type places (malls, department
stores, libraries, museums, community centers) at least {CLOSER_BY_M} m closer, in a straight line,
than our nearest refuge.

| Metric | Value |
|---|---|
| Hexagons where Amazon Location knows a refuge-type place clearly closer | {pct(res['gap_share'])} |
| Share of the sampled older adults living in those hexagons | {pct(res['gap_pop60_share'])} |

So the headline figure (older adults more than 15 minutes from a refuge, from open data) is best
read as an upper bound. Amazon's categories don't say whether a place is air-conditioned or lets
people stay, so not every one of those places is a real refuge either.

Billable requests for checks 1 and 2: {res['calls']}."""


def report_spot(res):
    exists = sum(1 for *_, e, _a in res["rows"] if e)
    agrees = sum(1 for *_, a in res["rows"] if a)
    rows = "\n".join(f"| {name} | {kind} | {'yes' if e else 'no'} | {'yes' if a else 'no'} |"
                     for name, kind, e, a in res["rows"])
    k = len(res["rows"])
    return f"""## 3. Spot-check of {k} random refuges

Random seed {res['seed']}, run on {res['date']}. For each refuge, Amazon Location `SearchText` for its
name near its location: is there a place with a similar name within 300 m, and does its category
agree with the type we assumed?

| Result | Count |
|---|---|
| Found by Amazon Location within 300 m | **{exists} of {k}** |
| ...and with a compatible category | **{agrees} of {k}** |

| Refuge (Overture) | Our type | Found | Category agrees |
|---|---|---|---|
{rows}

Billable requests for check 3: {res['calls']}."""


HEADER = """# Validation against Amazon Location Service

Generated by `pipeline/evidence.py`. Only these aggregate numbers are kept: the Amazon Location
responses were used once and not stored (IntendedUse "SingleUse").

<!-- BEGIN:routes -->
<!-- END:routes -->

<!-- BEGIN:spot -->
<!-- END:spot -->
"""


def update_section(path, name, text):
    """Replace one section of docs/validation.md, keeping the others (each check can run alone)."""
    doc = path.read_text() if path.exists() else HEADER
    pattern = re.compile(rf"(<!-- BEGIN:{name} -->)(.*?)(<!-- END:{name} -->)", re.S)
    path.write_text(pattern.sub(lambda m: f"{m.group(1)}\n{text}\n{m.group(3)}", doc))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("city")
    parser.add_argument("--parts", default="routes,spot", help="which checks to run: routes, spot or both")
    parser.add_argument("--n", type=int, default=50, help="hexagons to compare (checks 1 and 2)")
    parser.add_argument("--spot", type=int, default=15, help="refuges to spot-check (check 3)")
    parser.add_argument("--region", default="us-west-2")
    args = parser.parse_args()
    parts = set(args.parts.split(","))
    out = DOCS / "validation.md"
    try:
        if "routes" in parts:
            res = run_routes(args.city, args.n, args.region)
            chart_path = DOCS / "assets" / f"k8_validation_{args.city}.png"
            chart(res, chart_path)
            update_section(out, "routes", report_routes(res, chart_path))
            print(f"median |diff| {res['median_abs_err']:.1f} min, within 2 min {pct(res['within_2'])}, "
                  f"gap {pct(res['gap_share'])} of hexagons")
        if "spot" in parts:
            res = run_spot(args.city, args.spot, args.region)
            update_section(out, "spot", report_spot(res))
            print(f"spot-check: found {sum(1 for *_, e, _a in res['rows'] if e)}/{len(res['rows'])}, "
                  f"category agrees {sum(1 for *_, a in res['rows'] if a)}/{len(res['rows'])}")
    except ClientError as e:
        print(f"Amazon Location error: {e}", file=sys.stderr)
        return 1
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
