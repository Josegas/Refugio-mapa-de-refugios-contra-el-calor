# Refugio - how far is the nearest cool place, on foot, in Culiacán's heat?

> Work in progress for the AWS Builder Center **Weekend Challenge: Map it** (Oct 31 – Nov 2, 2026).
> Live app, write-up and video: coming soon.

Culiacán, Mexico, reaches 45 °C. For the older adults who walk in that heat, **Refugio** shows how many
minutes on foot the nearest cool place is, where those places are missing, and which existing public
buildings could open as heat refuges.

- **Planning layer** (precomputed from open data on AWS): walking minutes from every H3 hexagon to the
  nearest refuge, and how many people aged 60+ live there.
- **Personal layer** (live, Amazon Location Service): type an address to see the area you can reach on
  foot in 5, 10 and 15 minutes and the walking route to the nearest refuge.

## Repository layout

| Path | What it is |
|---|---|
| `pipeline/` | Python pipeline: `fetch.py` downloads the open data, `build.py` computes walking access |
| `web/` | Static web app (MapLibre GL JS); `web/data/` holds the generated data |
| `docs/` | Development journal and evidence |

## Reproduce the data

No AWS account is needed: both datasets are public buckets on the Registry of Open Data on AWS.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r pipeline/requirements.txt
python pipeline/fetch.py culiacan   # reads only the city's bounding box from Amazon S3
python pipeline/build.py culiacan   # writes web/data/culiacan/
```

## Data sources

- [Overture Maps](https://docs.overturemaps.org/) — places, transportation and divisions, release 2026-10-21.0
- [Meta High Resolution Settlement Layer](https://registry.opendata.aws/dataforgood-fb-hrsl/) — total population and people aged 60+

## License

Code: [MIT](LICENSE). Data in `web/data/`: ODbL 1.0, with the attributions listed in [DATA_LICENSE.md](DATA_LICENSE.md).
