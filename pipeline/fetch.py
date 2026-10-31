"""Download the open data for one city straight from the Registry of Open Data on AWS (Amazon S3).

  - Overture Maps places, road segments and city/neighborhood boundaries (GeoParquet on S3)
  - Meta High Resolution Settlement Layer: total population and people aged 60+ (Cloud-Optimized GeoTIFFs on S3)

Only the city's bounding box is read: DuckDB and GDAL use HTTP range requests,
so a city downloads in seconds instead of pulling global files.

Usage:  python fetch.py culiacan
"""
import json
import os
import sys
from pathlib import Path

import duckdb
import numpy as np
import rasterio
from rasterio.windows import from_bounds

from cities import CITIES, OVERTURE_RELEASE, HRSL_VERSION

OVERTURE = f"s3://overturemaps-us-west-2/release/{OVERTURE_RELEASE}"
HRSL = "https://dataforgood-fb-data.s3.amazonaws.com/hrsl-cogs/{layer}/{layer}-{version}.vrt"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def connect():
    con = duckdb.connect()
    con.sql("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    con.sql("SET geometry_always_xy = true;")
    # Public buckets: read anonymously even if AWS credentials are present in the environment.
    con.sql("CREATE SECRET anon (TYPE s3, PROVIDER config, KEY_ID '', SECRET '', REGION 'us-west-2')")
    return con


def bbox_filter(b, pad=0.0):
    xmin, ymin, xmax, ymax = b
    return (f"bbox.xmin > {xmin - pad} AND bbox.xmax < {xmax + pad} "
            f"AND bbox.ymin > {ymin - pad} AND bbox.ymax < {ymax + pad}")


def fetch(city_id):
    city = CITIES[city_id]
    out = RAW / city_id
    out.mkdir(parents=True, exist_ok=True)
    con = connect()
    bf = bbox_filter(city["bbox"])

    print(f"[{city_id}] places…")
    con.sql(f"""COPY (
        SELECT id, names.primary AS name, taxonomy.primary AS cat, basic_category,
               brand.names.primary AS brand, confidence, operating_status,
               addresses[1].freeform AS addr, ST_X(geometry) AS lon, ST_Y(geometry) AS lat
        FROM read_parquet('{OVERTURE}/theme=places/type=place/*', hive_partitioning=1)
        WHERE {bf}) TO '{out}/places.parquet'""")

    print(f"[{city_id}] road segments…")
    con.sql(f"""COPY (
        SELECT id, class, subclass, connectors, ST_AsWKB(geometry) AS wkb
        FROM read_parquet('{OVERTURE}/theme=transportation/type=segment/*', hive_partitioning=1)
        WHERE subtype = 'road' AND {bf}) TO '{out}/segments.parquet'""")

    print(f"[{city_id}] boundaries…")
    xmin, ymin, xmax, ymax = city["bbox"]
    con.sql(f"""COPY (
        SELECT id, subtype, names.primary AS name, ST_AsWKB(geometry) AS wkb
        FROM read_parquet('{OVERTURE}/theme=divisions/type=division_area/*', hive_partitioning=1)
        WHERE bbox.xmin < {xmax} AND bbox.xmax > {xmin} AND bbox.ymin < {ymax} AND bbox.ymax > {ymin}
          AND subtype IN ('locality', 'neighborhood', 'microhood', 'macrohood')
        ) TO '{out}/divisions.parquet'""")

    print(f"[{city_id}] population rasters…")
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    meta = {}
    for key, layer in (("pop", "hrsl_general"), ("pop60", "hrsl_elderly_60_plus")):
        url = "/vsicurl/" + HRSL.format(layer=layer, version=HRSL_VERSION)
        with rasterio.open(url) as src:
            win = from_bounds(xmin, ymin, xmax, ymax, src.transform)
            arr = src.read(1, window=win).astype("float32")
            arr[~np.isfinite(arr)] = 0
            np.save(out / f"{key}.npy", arr)
            t = src.window_transform(win)
            meta[key] = {"transform": list(t)[:6], "shape": arr.shape, "source": url.replace("/vsicurl/", "")}
    (out / "raster_meta.json").write_text(json.dumps(meta, indent=1))
    print(f"[{city_id}] done → {out}")


if __name__ == "__main__":
    for cid in sys.argv[1:] or ["culiacan"]:
        fetch(cid)
