"""Sanity checks on the generated data in web/data/<city>/ (the files the web app loads).

They catch a broken pipeline run before it reaches the live map.
"""
import json

import pytest

from build import PRIVATE, norm
from conftest import WEB_DATA

CITIES = sorted(p.name for p in WEB_DATA.iterdir() if (p / "stats.json").exists()) if WEB_DATA.exists() else []


def load(city):
    stats = json.loads((WEB_DATA / city / "stats.json").read_text())
    hexes = json.loads((WEB_DATA / city / "hex.json").read_text())
    proposals = json.loads((WEB_DATA / city / "proposals.geojson").read_text())
    return stats, hexes, proposals


def test_there_is_at_least_one_city():
    assert CITIES, "web/data/ has no city outputs: run `python pipeline/build.py culiacan`"


@pytest.mark.parametrize("city", CITIES)
def test_bands_add_up_to_total_60plus(city):
    """Every older adult falls in exactly one walking-time band."""
    stats, _, _ = load(city)
    total = stats["population"]["pop60"]
    for layer in ("access_refugio", "access_any"):
        bands = sum(b["pop60"] for b in stats[layer].values())
        assert abs(bands - total) <= len(stats[layer]), f"{layer}: bands sum {bands} != total {total}"


@pytest.mark.parametrize("city", CITIES)
def test_relief_never_makes_access_worse(city):
    """Adding relief stores can only shorten the walk: 'any' <= 'ref' in every hexagon."""
    _, hexes, _ = load(city)
    i_ref, i_any = hexes["fields"].index("ref"), hexes["fields"].index("any")
    bad = [r[0] for r in hexes["rows"] if r[i_any] > r[i_ref] + 1e-9]
    assert not bad, f"{len(bad)} hexagons have any > ref, e.g. {bad[:3]}"


@pytest.mark.parametrize("city", CITIES)
def test_proposals_are_public_buildings(city):
    """No private schools, clubs or temples among the proposed new refuges."""
    _, _, proposals = load(city)
    for f in proposals["features"]:
        p = f["properties"]
        assert p["type"] in {"escuela", "social", "gobierno", "deportivo"}, p
        assert not PRIVATE.search(norm(p["name"])), p["name"]
