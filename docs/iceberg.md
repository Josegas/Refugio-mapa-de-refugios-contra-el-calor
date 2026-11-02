# Refugio's results as an Apache Iceberg table

Written by `pipeline/iceberg.py` on 2026-11-01. Whole run (Parquet, upload, table, 3 commits
and 4 queries): 26 s.

The hexagons of the three cities (walking minutes, population and nearest refuge, from `web/data/`) are an
Apache Iceberg table in Amazon S3, registered in the AWS Glue Data Catalog and queried with Amazon Athena.
Each city was added with its own `INSERT`, so the table keeps one snapshot per city: a new city is one more
commit, and earlier versions can still be queried. Infrastructure: `infra/analytics.tf`.

Only our own open-data results are stored. Nothing from Amazon Location Places is saved.

The table holds the values exactly as published for the map: minutes rounded to 0.1 and population to 0.01 per
hexagon. That is why its "more than 15 min" totals are slightly lower (by under 1%) than in `stats.json`, which is
computed before rounding: a hexagon at 15.04 minutes is stored as 15.0 and no longer counts as "more than 15".

### Older adults more than a 15-minute walk from a refuge, by city

```sql
SELECT city,
       ROUND(SUM(population_60_plus)) AS older_adults,
       ROUND(SUM(CASE WHEN minutes_to_refuge > 15 THEN population_60_plus ELSE 0 END)) AS more_than_15_min,
       ROUND(100 * SUM(CASE WHEN minutes_to_refuge > 15 THEN population_60_plus ELSE 0 END)
             / SUM(population_60_plus), 1) AS pct
FROM refugio.hexagons
GROUP BY city
ORDER BY more_than_15_min DESC
```

| city | older_adults | more_than_15_min | pct |
|---|---|---|---|
| hermosillo | 63621.0 | 18715.0 | 29.4 |
| culiacan | 55484.0 | 17368.0 | 31.3 |
| mexicali | 61403.0 | 16104.0 | 26.2 |

*Athena: 661 ms, 83 KB scanned.*

### Which kind of place is the nearest refuge for older adults who live more than 15 minutes away (Culiacán)

```sql
SELECT nearest_refuge_type,
       ROUND(SUM(population_60_plus)) AS older_adults_far_away
FROM refugio.hexagons
WHERE city = 'culiacan' AND minutes_to_refuge > 15
GROUP BY nearest_refuge_type
ORDER BY older_adults_far_away DESC
```

| nearest_refuge_type | older_adults_far_away |
|---|---|
| super | 6136.0 |
| plaza | 3939.0 |
| comunitario | 3617.0 |
| departamental | 2211.0 |
| museo | 1281.0 |
| biblioteca | 161.0 |
|  | 24.0 |

*Athena: 638 ms, 28 KB scanned.*

### The table's history: one Iceberg snapshot per city added

```sql
SELECT committed_at, snapshot_id, operation,
       summary['added-records'] AS added_rows
FROM refugio."hexagons$snapshots"
ORDER BY committed_at
```

| committed_at | snapshot_id | operation | added_rows |
|---|---|---|---|
| 2026-11-02 05:24:00.514 UTC | 4694074088263641893 | append | 6932 |
| 2026-11-02 05:24:02.597 UTC | 2517722614701675186 | append | 7478 |
| 2026-11-02 05:24:04.449 UTC | 5516165133668960128 | append | 9504 |

*Athena: 631 ms, 2 KB scanned.*

### Time travel: the table as it was after the first commit (Culiacán only)

```sql
SELECT city, COUNT(*) AS hexagons
FROM refugio.hexagons FOR VERSION AS OF 4694074088263641893
GROUP BY city
```

| city | hexagons |
|---|---|
| culiacan | 6932 |

*Athena: 1321 ms, 0 KB scanned.*
