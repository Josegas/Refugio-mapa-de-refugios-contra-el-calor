"""Publish the pipeline's results as an Apache Iceberg table on Amazon S3 and query it with Amazon Athena.

Why: web/data/ is made for the map (small JSON files). The same results as an Iceberg table can be
queried with plain SQL by anyone with access (a city analyst, for example) without touching this code,
and every city added is one more commit (snapshot) of the same table, with its history.

What it does:
  1. Writes one Parquet file per city from web/data/<city>/ (hexagons + nearest refuge) with DuckDB.
  2. Uploads them to s3://<analytics bucket>/staging/hexagons/.
  3. In Athena: creates the Iceberg table refugio.hexagons and INSERTs each city (one snapshot per city).
  4. Runs the example queries and writes their results, data scanned and time to docs/iceberg.md.

Only our own open-data results go to S3. Nothing from Amazon Location Places is stored.
The infrastructure (bucket, Glue database, Athena workgroup) is in infra/analytics.tf.

Usage:  export AWS_PROFILE=refugio
        python pipeline/iceberg.py --bucket <analytics_bucket output of terraform>
Cost:   each Athena query is billed for at least 10 MB scanned ($5/TB): about $0.00005 per query.
"""
import argparse
import json
import tempfile
import time
from datetime import date
from pathlib import Path

import boto3
import duckdb

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
REGION = "us-west-2"
DATABASE = "refugio"
WORKGROUP = "refugio"
CITIES = ["culiacan", "hermosillo", "mexicali"]

COLUMNS = """
  city                string,
  h3_cell             string,
  minutes_to_refuge   double,
  minutes_to_any      double,
  population          double,
  population_60_plus  double,
  nearest_refuge      string,
  nearest_refuge_type string
"""

# The questions shown in docs/iceberg.md (and in the article). {db} is replaced by the database name.
QUERIES = [
    ("Older adults more than a 15-minute walk from a refuge, by city", """
SELECT city,
       ROUND(SUM(population_60_plus)) AS older_adults,
       ROUND(SUM(CASE WHEN minutes_to_refuge > 15 THEN population_60_plus ELSE 0 END)) AS more_than_15_min,
       ROUND(100 * SUM(CASE WHEN minutes_to_refuge > 15 THEN population_60_plus ELSE 0 END)
             / SUM(population_60_plus), 1) AS pct
FROM {db}.hexagons
GROUP BY city
ORDER BY more_than_15_min DESC"""),
    ("Which kind of place is the nearest refuge for older adults who live more than 15 minutes away (Culiacán)", """
SELECT nearest_refuge_type,
       ROUND(SUM(population_60_plus)) AS older_adults_far_away
FROM {db}.hexagons
WHERE city = 'culiacan' AND minutes_to_refuge > 15
GROUP BY nearest_refuge_type
ORDER BY older_adults_far_away DESC"""),
    ("The table's history: one Iceberg snapshot per city added", """
SELECT committed_at, snapshot_id, operation,
       summary['added-records'] AS added_rows
FROM {db}."hexagons$snapshots"
ORDER BY committed_at"""),
    ("Time travel: the table as it was after the first commit (Culiacán only)", """
SELECT city, COUNT(*) AS hexagons
FROM {db}.hexagons FOR VERSION AS OF {first_snapshot}
GROUP BY city"""),
]


def city_rows(city):
    """One row per hexagon: the map's minutes and population, plus the name of the nearest refuge."""
    hex_ = json.loads((WEB / "data" / city / "hex.json").read_text())
    refuges = json.loads((WEB / "data" / city / "refuges.geojson").read_text())["features"]
    col = {name: i for i, name in enumerate(hex_["fields"])}
    rows = []
    for r in hex_["rows"]:
        i = r[col["iref"]]
        place = refuges[i]["properties"] if i is not None and i >= 0 else {}
        rows.append((city, r[col["h"]], r[col["ref"]], r[col["any"]], r[col["pop"]], r[col["pop60"]],
                     place.get("n"), place.get("t")))
    return rows


def write_parquet(city, folder):
    """DuckDB writes the Parquet file (no extra libraries needed)."""
    path = Path(folder) / f"{city}.parquet"
    con = duckdb.connect()
    con.execute(f"CREATE TABLE t ({COLUMNS.replace('string', 'VARCHAR').replace('double', 'DOUBLE')})")
    con.executemany("INSERT INTO t VALUES (?, ?, ?, ?, ?, ?, ?, ?)", city_rows(city))
    con.execute(f"COPY t TO '{path}' (FORMAT parquet)")
    con.close()
    return path


class Athena:
    """Runs one SQL statement at a time in the refugio workgroup and waits for it."""

    def __init__(self):
        self.client = boto3.client("athena", region_name=REGION)

    def run(self, sql):
        qid = self.client.start_query_execution(QueryString=sql, WorkGroup=WORKGROUP,
                                                QueryExecutionContext={"Database": DATABASE})["QueryExecutionId"]
        while True:
            q = self.client.get_query_execution(QueryExecutionId=qid)["QueryExecution"]
            state = q["Status"]["State"]
            if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
                break
            time.sleep(0.5)
        if state != "SUCCEEDED":
            raise SystemExit(f"Athena query {state}: {q['Status'].get('StateChangeReason')}\n{sql}")
        return qid, q["Statistics"]

    def rows(self, qid):
        result = self.client.get_query_results(QueryExecutionId=qid)["ResultSet"]["Rows"]
        return [[c.get("VarCharValue", "") for c in r["Data"]] for r in result]


def empty_prefix(s3, bucket, prefix):
    """Deletes old files under a prefix, so every run starts from a clean table."""
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        keys = [{"Key": o["Key"]} for o in page.get("Contents", [])]
        if keys:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": keys})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bucket", required=True, help="analytics bucket (terraform output analytics_bucket)")
    args = ap.parse_args()
    bucket = args.bucket
    s3 = boto3.client("s3", region_name=REGION)
    athena = Athena()
    t0 = time.perf_counter()

    # 1-2) Parquet files to S3 (staging area that Athena reads as a plain table)
    print("1/4 Parquet files -> S3")
    empty_prefix(s3, bucket, "staging/hexagons/")
    with tempfile.TemporaryDirectory() as tmp:
        for city in CITIES:
            path = write_parquet(city, tmp)
            s3.upload_file(str(path), bucket, f"staging/hexagons/{city}.parquet")
            print(f"    {city}: {path.stat().st_size / 1024:.0f} KB")

    # 3) The Iceberg table, then one INSERT (= one snapshot) per city
    print("2/4 Iceberg table")
    athena.run("DROP TABLE IF EXISTS hexagons_staging")
    athena.run(f"CREATE EXTERNAL TABLE hexagons_staging ({COLUMNS}) STORED AS PARQUET "
               f"LOCATION 's3://{bucket}/staging/hexagons/'")
    athena.run("DROP TABLE IF EXISTS hexagons")
    empty_prefix(s3, bucket, "iceberg/hexagons/")
    athena.run(f"CREATE TABLE hexagons ({COLUMNS}) PARTITIONED BY (city) "
               f"LOCATION 's3://{bucket}/iceberg/hexagons/' TBLPROPERTIES ('table_type' = 'ICEBERG')")
    for city in CITIES:
        athena.run(f"INSERT INTO hexagons SELECT * FROM hexagons_staging WHERE city = '{city}'")
        print(f"    + {city}")
    athena.run("DROP TABLE hexagons_staging")  # the staging table was only a bridge

    # 4) Example queries -> docs/iceberg.md
    print("3/4 Example queries")
    snaps_qid, _ = athena.run(f"SELECT snapshot_id FROM \"hexagons$snapshots\" ORDER BY committed_at LIMIT 1")
    first_snapshot = athena.rows(snaps_qid)[1][0]
    sections = []
    for title, sql in QUERIES:
        sql = sql.format(db=DATABASE, first_snapshot=first_snapshot).strip()
        qid, stats = athena.run(sql)
        rows = athena.rows(qid)
        table = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])]
        table += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        sections.append(f"### {title}\n\n```sql\n{sql}\n```\n\n" + "\n".join(table) +
                        f"\n\n*Athena: {stats['EngineExecutionTimeInMillis']} ms, "
                        f"{stats['DataScannedInBytes'] / 1024:.0f} KB scanned.*\n")
        print(f"    {title[:60]}... {stats['EngineExecutionTimeInMillis']} ms")

    print("4/4 docs/iceberg.md")
    total = time.perf_counter() - t0
    (ROOT / "docs" / "iceberg.md").write_text(f"""# Refugio's results as an Apache Iceberg table

Written by `pipeline/iceberg.py` on {date.today().isoformat()}. Whole run (Parquet, upload, table, {len(CITIES)} commits
and {len(QUERIES)} queries): {total:.0f} s.

The hexagons of the three cities (walking minutes, population and nearest refuge, from `web/data/`) are an
Apache Iceberg table in Amazon S3, registered in the AWS Glue Data Catalog and queried with Amazon Athena.
Each city was added with its own `INSERT`, so the table keeps one snapshot per city: a new city is one more
commit, and earlier versions can still be queried. Infrastructure: `infra/analytics.tf`.

Only our own open-data results are stored. Nothing from Amazon Location Places is saved.

The table holds the values exactly as published for the map: minutes rounded to 0.1 and population to 0.01 per
hexagon. That is why its "more than 15 min" totals are slightly lower (by under 1%) than in `stats.json`, which is
computed before rounding: a hexagon at 15.04 minutes is stored as 15.0 and no longer counts as "more than 15".

""" + "\n".join(sections))
    print(f"done in {total:.0f} s")


if __name__ == "__main__":
    main()
