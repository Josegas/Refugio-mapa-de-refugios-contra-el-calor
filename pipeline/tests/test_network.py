"""Checks that the walking network built from Overture is realistic.

"Detour factor" = distance walking along the streets / straight-line distance. In real cities it is
usually around 1.2-1.4. A value near 1.0 would mean the graph has fake shortcuts; a value near 2+
would mean streets are missing or badly connected.

Needs the raw downloads in data/raw/<city>/ (not stored in git), so it is skipped where they don't
exist, e.g. in GitHub Actions.
"""
import numpy as np
import pytest
from pyproj import Geod
from scipy.sparse.csgraph import dijkstra

from conftest import RAW

CITY = "culiacan"
pytestmark = pytest.mark.skipif(not (RAW / CITY / "segments.parquet").exists(),
                                reason="raw data not downloaded (run pipeline/fetch.py culiacan)")


def test_detour_factor_is_realistic():
    from build import build_graph
    G, coords, in_main, _ = build_graph(CITY)
    nodes = np.nonzero(in_main)[0]
    rng = np.random.default_rng(42)          # fixed seed: same result every run
    sources = rng.choice(nodes, 40, replace=False)
    targets = rng.choice(nodes, 400, replace=False)
    dist = dijkstra(G, directed=False, indices=sources)[:, targets]   # metres along streets

    geod = Geod(ellps="WGS84")
    ratios = []
    for i, s in enumerate(sources):
        for j, t in enumerate(targets):
            straight = geod.inv(coords[s, 0], coords[s, 1], coords[t, 0], coords[t, 1])[2]
            if 500 <= straight <= 5000 and np.isfinite(dist[i, j]):
                ratios.append(dist[i, j] / straight)
    median = float(np.median(ratios))
    assert len(ratios) > 1000
    assert 1.05 <= median <= 1.6, f"median detour factor {median:.2f}"
