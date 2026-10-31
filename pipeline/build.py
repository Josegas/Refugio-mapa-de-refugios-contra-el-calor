"""Compute walking access to cool refuges for one city and write the web data files.

Steps
 1. Classify Overture places into "refugio" (a cool place where you can stay without
    buying anything) and "alivio" (an air-conditioned shop where you can buy water).
 2. Build a walking network from Overture road segments (split at connectors).
 3. Aggregate Meta HRSL population (total and 60+) into H3 hexagons inside the city.
 4. Multi-source Dijkstra from every refuge -> walking minutes to the nearest one.
 5. Greedy maximum-coverage: which existing public buildings (public schools, government
    offices, community centers, sports units) would bring the most uncovered older adults
    within 10 minutes.

Usage:  python build.py culiacan
"""
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import duckdb
import h3
import numpy as np
from pyproj import Geod
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree
from shapely import wkb as swkb
from shapely.geometry import Point
from shapely.ops import linemerge
from shapely.prepared import prep
from shapely.strtree import STRtree

from cities import (CITIES, COVER_MIN, H3_RES, HRSL_VERSION, MAX_SNAP_M, N_PROPOSALS,
                    OVERTURE_RELEASE, THRESHOLDS_MIN, WALK_SPEED_MS)

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
WEB = ROOT / "web" / "data"
GEOD = Geod(ellps="WGS84")
MAX_MIN = 60  # minutes beyond which we stop searching ("60+")


# ----------------------------------------------------------------------------- places

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.lower()).strip()


REFUGIO_CATS = {
    "shopping_mall": "plaza", "department_store": "departamental",
    "library": "biblioteca", "museum": "museo", "history_museum": "museo", "art_museum": "museo",
    "science_museum": "museo", "design_museum": "museo", "children_museum": "museo",
    "cultural_center": "cultura", "community_center": "comunitario",
    "senior_citizen_service": "comunitario", "town_hall": "comunitario",
}
SUPER_CATS = {"grocery_store", "supermarket", "hypermarket", "department_store",
              "discount_store", "warehouse_store", "food_and_beverage_store"}
SUPERMARKET = re.compile(r"\b(soriana|walmart|bodega aurrera|aurrera|sam.?s club|costco|casa ley|"
                         r"ley express|super ley|chedraui|s-mart|city club|la comer|fresko|calimax|"
                         r"smart & final|santa fe)\b|(^|\s)ley(\s|$)")
DIF = re.compile(r"\bdif\b")
SOCIAL_CATS = {"government_office", "social_or_community_service", "community_and_government",
               "community_center"}
PHARMACY_CATS = {"pharmacy", "drugstore", "pharmacy_and_drug_store"}
CONV_CATS = {"convenience_store", "grocery_store", "gas_station", "food_and_beverage_store"}
CHAIN_CONV = re.compile(r"\b(oxxo|kiosko|7[- ]?eleven|circle ?k|tiendas? six|extra)\b")
EXCLUDE = re.compile(r"bancoppel|afore|zona de comida|5\.11|amway|panteon|cementerio|penitenciari|\bpenal\b|"
                     r"funera|velatorio|estacionamiento|deposito|modelorama|cajero|\batm\b|bodega de|"
                     r"oficinas? corporativ|almacen|cedis|gasolin")

# Candidates for NEW refuges must be existing PUBLIC buildings: a public-policy proposal can't rely on
# private or religious property (see docs/journal.md, 2026-10-31 14:29). Temples are not candidates.
CANDIDATE_CATS = {
    "school": "escuela", "public_school": "escuela", "elementary_school": "escuela",
    "middle_school": "escuela", "high_school": "escuela", "preschool": "escuela",
    "social_or_community_service": "social", "community_and_government": "social",
    "government_office": "gobierno", "sports_and_recreation": "deportivo",
}
# Names that usually mean a private place: private schools, clubs, daycares, gyms, civil associations
# ("A.C.", "I.A.P."), foundations, unions and political parties
PRIVATE = re.compile(r"\b(instituto|colegio|liceo|academy|academia|montessori|club|estancia infantil|"
                     r"guarderia|bilingue|kinder privado|gym|fitness|fundacion|asociacion|sindicato|partido|"
                     r"iap|iarp)\b|\ba\.\s?c\b|\bi\.\s?a\.\s?p\b")
# A school only counts if its name looks like a public school
PUBLIC_SCHOOL = re.compile(r"\b(escuela|primaria|secundaria|telesecundaria|jardin de ninos|preescolar|cbtis|"
                           r"cetis|conalep|cobaes|bachillerato|preparatoria|eti|uas)\b")
# Overture's government/social/sports categories are very noisy (banks, gyms, NGOs, the prison...),
# so a non-school candidate only counts if its name says it is one of the public buildings in the
# definition (CLAUDE.md §2): sindicatura, municipal delegation, community center, house of culture,
# or a public sports unit.
PUBLIC_OTHER = re.compile(r"\b(sindicatura|centros? comunitarios?|centro de desarrollo comunitario|cdc|"
                          r"casa de la cultura|unidad deportiva|polideportivo|isde|ayuntamiento|"
                          r"presidencia municipal)\b|\bdelegacion (norte|sur|oriente|poniente)\b|"
                          r"\bdelegacion .*gobierno de culiacan")
MIN_CONFIDENCE = 0.5


def candidate_type(name, cat):
    """Return the candidate type ('escuela', 'social', ...) if this place can be proposed as a new
    public refuge, else None."""
    n = norm(name)
    if not n or cat not in CANDIDATE_CATS or EXCLUDE.search(n) or PRIVATE.search(n):
        return None
    kind = CANDIDATE_CATS[cat]
    public = PUBLIC_SCHOOL if kind == "escuela" else PUBLIC_OTHER
    if not public.search(n):
        return None
    return kind


def classify(name, cat):
    n = norm(name)
    if not n or EXCLUDE.search(n):
        return None
    if cat in SUPER_CATS and SUPERMARKET.search(n):
        return ("refugio", "super")
    if cat in REFUGIO_CATS:
        return ("refugio", REFUGIO_CATS[cat])
    if cat in SOCIAL_CATS and DIF.search(n):
        return ("refugio", "comunitario")
    if cat in PHARMACY_CATS:
        return ("alivio", "farmacia")
    if cat in CONV_CATS and CHAIN_CONV.search(n):
        return ("alivio", "conveniencia")
    return None


def dedupe(items, radius_m=40):
    """Drop near-duplicate POIs (same normalized name within radius), keep highest confidence."""
    items = sorted(items, key=lambda r: -r["conf"])
    kept, by_name = [], defaultdict(list)
    for r in items:
        key = norm(r["name"])[:14]
        if any(GEOD.inv(r["lon"], r["lat"], k["lon"], k["lat"])[2] < radius_m for k in by_name[key]):
            continue
        by_name[key].append(r)
        kept.append(r)
    return kept


def load_places(city_id, locality_poly):
    rows = duckdb.sql(f"SELECT name, cat, confidence, operating_status, lon, lat "
                      f"FROM '{RAW / city_id / 'places.parquet'}'").fetchall()
    refuges, candidates = [], []
    lp = prep(locality_poly.buffer(0.01))  # ~1 km margin around the city edge
    for name, cat, conf, status, lon, lat in rows:
        if conf is None or conf < MIN_CONFIDENCE or status == "closed" or not lp.contains(Point(lon, lat)):
            continue
        c = classify(name, cat)
        if c:
            refuges.append({"name": name.strip(), "tier": c[0], "type": c[1], "conf": conf, "lon": lon, "lat": lat})
        elif (kind := candidate_type(name, cat)):
            candidates.append({"name": (name or "").strip(), "type": kind, "conf": conf,
                               "lon": lon, "lat": lat})
    return dedupe(refuges), dedupe(candidates)


# ----------------------------------------------------------------------------- network

def build_graph(city_id):
    segs = duckdb.sql(f"SELECT class, connectors, wkb FROM '{RAW / city_id / 'segments.parquet'}'").fetchall()
    node_of, coords, edges = {}, [], {}
    street_m = 0.0
    for cls, conns, wkbb in segs:
        if cls == "motorway" or not conns:
            continue
        line = swkb.loads(bytes(wkbb))
        if line.geom_type == "MultiLineString":
            line = linemerge(line)
            if line.geom_type != "LineString":
                continue
        length = GEOD.geometry_length(line)
        street_m += length
        prev = prev_at = None
        for c in sorted(conns, key=lambda c: c["at"]):
            cid, at = c["connector_id"], c["at"]
            if cid not in node_of:
                p = line.interpolate(at, normalized=True)
                node_of[cid] = len(coords)
                coords.append((p.x, p.y))
            n = node_of[cid]
            if prev is not None and n != prev:
                key = (min(prev, n), max(prev, n))
                w = max((at - prev_at) * length, 0.5)
                if w < edges.get(key, 1e18):
                    edges[key] = w
            prev, prev_at = n, at
    coords = np.array(coords)
    a = np.fromiter((k[0] for k in edges), int, len(edges))
    b = np.fromiter((k[1] for k in edges), int, len(edges))
    w = np.fromiter(edges.values(), float, len(edges))
    N = len(coords)
    G = coo_matrix((np.r_[w, w], (np.r_[a, b], np.r_[b, a])), shape=(N, N)).tocsr()
    ncomp, labels = connected_components(G, directed=False)
    main = np.argmax(np.bincount(labels))
    in_main = labels == main
    return G, coords, in_main, {"nodes": int(N), "edges": int(len(edges)), "street_km": round(street_m / 1000),
                                "main_component_share": round(float(in_main.mean()), 3)}


class Projector:
    """Local equirectangular projection (metres) good enough for city-scale snapping."""
    def __init__(self, lon0, lat0):
        self.lon0, self.lat0 = lon0, lat0
        self.kx = 111320 * np.cos(np.radians(lat0))
        self.ky = 110574

    def __call__(self, lon, lat):
        return np.c_[(np.asarray(lon) - self.lon0) * self.kx, (np.asarray(lat) - self.lat0) * self.ky]


# ----------------------------------------------------------------------------- population

def load_hexes(city_id, locality_poly):
    meta = json.loads((RAW / city_id / "raster_meta.json").read_text())
    pop = np.load(RAW / city_id / "pop.npy")
    pop60 = np.load(RAW / city_id / "pop60.npy")
    a, b, c, d, e, f = meta["pop"]["transform"]
    assert meta["pop"]["transform"] == meta["pop60"]["transform"]
    rr, cc = np.nonzero((pop > 0) | (pop60 > 0))
    lon = c + a * (cc + 0.5) + b * (rr + 0.5)
    lat = f + d * (cc + 0.5) + e * (rr + 0.5)
    sums = defaultdict(lambda: [0.0, 0.0])
    for i in range(len(rr)):
        h = h3.latlng_to_cell(lat[i], lon[i], H3_RES)
        s = sums[h]
        s[0] += float(pop[rr[i], cc[i]])
        s[1] += float(pop60[rr[i], cc[i]])
    lp = prep(locality_poly)
    hexes = []
    for h, (p, p60) in sums.items():
        la, lo = h3.cell_to_latlng(h)
        if lp.contains(Point(lo, la)):
            hexes.append({"h": h, "lon": lo, "lat": la, "pop": p, "pop60": p60})
    return hexes


# ----------------------------------------------------------------------------- neighborhoods

def load_divisions(city_id, locality_name):
    rows = duckdb.sql(f"SELECT subtype, name, wkb FROM '{RAW / city_id / 'divisions.parquet'}'").fetchall()
    locality, hoods = None, []
    for st, name, g in rows:
        geom = swkb.loads(bytes(g))
        if st == "locality" and name == locality_name:
            locality = geom if locality is None or geom.area > locality.area else locality
        elif st in ("neighborhood", "microhood", "macrohood") and name:
            hoods.append((name, geom))
    if locality is None:
        raise SystemExit(f"Locality polygon '{locality_name}' not found; check cities.py")
    return locality, hoods


def name_points(points, hoods, max_deg=0.003):
    if not hoods:
        return [None] * len(points)
    geoms = [g for _, g in hoods]
    tree = STRtree(geoms)
    out = []
    for lon, lat in points:
        p = Point(lon, lat)
        hits = list(tree.query(p, predicate="intersects"))
        if hits:
            out.append(hoods[min(hits, key=lambda i: geoms[i].area)][0])
            continue
        j = tree.query_nearest(p, max_distance=max_deg)
        out.append(hoods[int(j[0])][0] if len(j) else None)
    return out


# ----------------------------------------------------------------------------- main

def band_stats(minutes, pop, pop60):
    out = {}
    lo = 0
    for t in THRESHOLDS_MIN:
        m = (minutes > lo) & (minutes <= t) if lo else (minutes <= t)
        out[f"le{t}"] = {"pop": round(float(pop[m].sum())), "pop60": round(float(pop60[m].sum()))}
        lo = t
    m = minutes > THRESHOLDS_MIN[-1]
    out[f"gt{THRESHOLDS_MIN[-1]}"] = {"pop": round(float(pop[m].sum())), "pop60": round(float(pop60[m].sum()))}
    return out


def build(city_id):
    city = CITIES[city_id]
    print(f"[{city_id}] boundaries")
    locality, hoods = load_divisions(city_id, city["locality"])
    print(f"[{city_id}] places")
    refuges, candidates = load_places(city_id, locality)
    print(f"[{city_id}] network")
    G, coords, in_main, gstats = build_graph(city_id)
    lon0, lat0 = city["center"]
    proj = Projector(lon0, lat0)
    main_idx = np.nonzero(in_main)[0]
    tree = cKDTree(proj(coords[main_idx, 0], coords[main_idx, 1]))

    def snap(items):
        d, i = tree.query(proj([r["lon"] for r in items], [r["lat"] for r in items]))
        return d, main_idx[i]

    print(f"[{city_id}] population")
    hexes = load_hexes(city_id, locality)
    hd, hn = snap(hexes)
    keep = hd <= MAX_SNAP_M
    dropped_pop = sum(h["pop"] for h, k in zip(hexes, keep) if not k)
    hexes = [h for h, k in zip(hexes, keep) if k]
    hd, hn = hd[keep], hn[keep]
    pop = np.array([h["pop"] for h in hexes])
    pop60 = np.array([h["pop60"] for h in hexes])

    rd, rn = snap(refuges)
    limit = MAX_MIN * 60 * WALK_SPEED_MS

    def access(mask):
        """Walking minutes from every hexagon to the nearest refuge in `mask`, plus which one."""
        idx = np.nonzero(mask & (rd <= 300))[0]
        best = {}
        for i in idx:  # one source per node, keep the refuge with the shortest snap
            if rn[i] not in best or rd[i] < rd[best[rn[i]]]:
                best[rn[i]] = i
        src_nodes = np.array(list(best.keys()))
        src_off = np.array([max(rd[best[s]], 0.01) for s in src_nodes])  # metres refuge door -> street
        # The walk from a refuge's door to its street node must count *inside* the search, otherwise a
        # refuge whose street node is near but whose door is far can win (a test caught this: adding
        # relief stores made 28 hexagons look farther). Trick: one virtual node V linked to every
        # refuge's street node with an edge as long as that door-to-street walk; then a single
        # Dijkstra from V gives every street node its distance to the truly nearest refuge door.
        N = G.shape[0]
        Gv = csr_matrix((G.data, G.indices, np.r_[G.indptr, G.indptr[-1]]), shape=(N + 1, N + 1))
        Gv = Gv + coo_matrix((src_off, (np.full(len(src_nodes), N), src_nodes)), shape=(N + 1, N + 1)).tocsr()
        dist, pred = dijkstra(Gv, directed=True, indices=N, return_predecessors=True, limit=limit)
        # Which refuge each street node was reached from: follow the shortest-path tree outward from V
        label = np.full(N + 1, -1)
        for n in np.argsort(dist):
            if n == N or not np.isfinite(dist[n]):
                continue
            label[n] = n if pred[n] == N else label[pred[n]]
        dn = dist[hn]  # already includes the door-to-street offset
        which = np.array([best.get(s, -1) for s in label[hn]])
        meters = dn + hd
        minutes = np.where(np.isfinite(meters), meters / WALK_SPEED_MS / 60, MAX_MIN + 1)
        minutes = np.minimum(minutes, MAX_MIN + 1)
        which = np.where(minutes <= MAX_MIN, which, -1)
        return minutes, which

    tiers = np.array([r["tier"] for r in refuges])
    print(f"[{city_id}] dijkstra")
    m_ref, w_ref = access(tiers == "refugio")
    m_any, w_any = access(np.ones(len(refuges), bool))

    # ---- proposals: greedy maximum coverage over existing public buildings
    print(f"[{city_id}] proposals ({len(candidates)} candidates)")
    cover_m = COVER_MIN * 60 * WALK_SPEED_MS
    cd, cn = snap(candidates) if candidates else (np.array([]), np.array([], int))
    ok = np.nonzero(cd <= 150)[0]
    covers = {}
    for s in range(0, len(ok), 64):
        batch = ok[s:s + 64]
        D = dijkstra(G, directed=False, indices=cn[batch], limit=cover_m)
        tot = D[:, hn] + hd[None, :] + cd[batch][:, None]
        for j, ci in enumerate(batch):
            covers[ci] = np.nonzero(tot[j] <= cover_m)[0]
    weight = np.where(m_ref > COVER_MIN, pop60, 0.0)
    weight_pop = np.where(m_ref > COVER_MIN, pop, 0.0)
    proposals = []
    for rank in range(1, N_PROPOSALS + 1):
        if not covers:
            break
        ci = max(covers, key=lambda k: weight[covers[k]].sum())
        gain = float(weight[covers[ci]].sum())
        if gain < 1:
            break
        c = candidates[ci]
        proposals.append({**{k: c[k] for k in ("name", "type", "lon", "lat")}, "rank": rank,
                          "new_pop60": round(gain), "new_pop": round(float(weight_pop[covers[ci]].sum()))})
        weight[covers[ci]] = 0
        weight_pop[covers[ci]] = 0
        del covers[ci]
    new60 = sum(p["new_pop60"] for p in proposals)
    newp = sum(p["new_pop"] for p in proposals)

    # ---- heat-desert zones: contiguous hexagons > 15 min from any refugio
    print(f"[{city_id}] zones")
    hood_names = name_points([(h["lon"], h["lat"]) for h in hexes], hoods)
    far = {hexes[i]["h"]: i for i in np.nonzero(m_ref > THRESHOLDS_MIN[-1])[0]}
    seen, zones = set(), []
    for h0 in far:
        if h0 in seen:
            continue
        comp, stack = [], [h0]
        seen.add(h0)
        while stack:
            h = stack.pop()
            comp.append(far[h])
            for nb in h3.grid_disk(h, 1):
                if nb in far and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        p60 = float(pop60[comp].sum())
        if p60 < 50:
            continue
        names = Counter(hood_names[i] for i in comp if hood_names[i])
        lon = float(np.average([hexes[i]["lon"] for i in comp], weights=pop60[comp] + 1e-6))
        lat = float(np.average([hexes[i]["lat"] for i in comp], weights=pop60[comp] + 1e-6))
        if not names:
            nm = name_points([(lon, lat)], hoods, max_deg=0.01)[0]
            names = Counter([nm] if nm else [])
        zones.append({"name": " / ".join(n for n, _ in names.most_common(2)) or None,
                      "lon": round(lon, 5), "lat": round(lat, 5), "pop60": round(p60),
                      "pop": round(float(pop[comp].sum())), "hexes": len(comp),
                      "median_min": round(float(np.median(m_ref[comp])))})
    zones.sort(key=lambda z: -z["pop60"])

    # ---- write outputs
    out = WEB / city_id
    out.mkdir(parents=True, exist_ok=True)
    rows = [[h["h"], round(float(m_ref[i]), 1), round(float(m_any[i]), 1), round(h["pop"], 1),
             round(h["pop60"], 2), int(w_ref[i]), int(w_any[i])] for i, h in enumerate(hexes)]
    (out / "hex.json").write_text(json.dumps({"res": H3_RES, "fields": ["h", "ref", "any", "pop", "pop60", "iref", "iany"],
                                               "rows": rows}, separators=(",", ":")))
    feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(r["lon"], 6), round(r["lat"], 6)]},
              "properties": {"i": i, "n": r["name"], "k": r["tier"], "t": r["type"]}} for i, r in enumerate(refuges)]
    (out / "refuges.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False,
                                                    separators=(",", ":")))
    pfeats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(p["lon"], 6), round(p["lat"], 6)]},
               "properties": {k: p[k] for k in ("rank", "name", "type", "new_pop60", "new_pop")}} for p in proposals]
    (out / "proposals.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": pfeats},
                                                      ensure_ascii=False, separators=(",", ":")))
    tot60, totp = float(pop60.sum()), float(pop.sum())
    le10_60 = float(pop60[m_ref <= COVER_MIN].sum())
    stats = {
        "city": city["name"], "state": city["state"], "id": city_id, "generated": date.today().isoformat(),
        "center": city["center"], "zoom": city["zoom"],
        "params": {"walk_speed_kmh": WALK_SPEED_MS * 3.6, "thresholds_min": THRESHOLDS_MIN, "cover_min": COVER_MIN,
                   "h3_res": H3_RES, "min_confidence": MIN_CONFIDENCE, "max_snap_m": MAX_SNAP_M},
        "sources": {"overture_release": OVERTURE_RELEASE, "hrsl_version": HRSL_VERSION},
        "network": gstats,
        "counts": {"refugio": int((tiers == "refugio").sum()), "alivio": int((tiers == "alivio").sum()),
                   "by_type": dict(Counter(r["type"] for r in refuges)), "candidates": len(candidates),
                   "hexes": len(hexes), "hoods": len(hoods)},
        "population": {"total": round(totp), "pop60": round(tot60), "dropped_far_from_streets": round(dropped_pop)},
        "access_refugio": band_stats(m_ref, pop, pop60),
        "access_any": band_stats(m_any, pop, pop60),
        "zones": zones[:10],
        "proposals": {"n": len(proposals), "new_pop60": new60, "new_pop": newp,
                      "pct60_le10_before": round(100 * le10_60 / tot60, 1),
                      "pct60_le10_after": round(100 * (le10_60 + new60) / tot60, 1)},
    }
    (out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    print(json.dumps({k: stats[k] for k in ("counts", "population", "access_refugio", "access_any", "proposals", "network")},
                     ensure_ascii=False, indent=1))
    print("zones:", json.dumps(zones[:6], ensure_ascii=False))
    print("proposals:", json.dumps(proposals, ensure_ascii=False))
    return stats


if __name__ == "__main__":
    for cid in sys.argv[1:] or ["culiacan"]:
        build(cid)
