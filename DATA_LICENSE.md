# Data license

The code in this repository is MIT-licensed (see `LICENSE`). This file covers only the **data**.

The files in `web/data/` (walking minutes per hexagon, refuge points, proposed new refuges and summary
statistics) are a derived database built from open datasets on the Registry of Open Data on AWS.
They are released under the **Open Database License (ODbL) v1.0**:
https://opendatacommons.org/licenses/odbl/1-0/

## Sources and required attribution

| Source | Used for | License | Attribution |
|---|---|---|---|
| Overture Maps Foundation, `transportation` (segments) and `divisions`, release 2026-10-21.0 | Walking network; city and neighborhood boundaries | ODbL 1.0 | © OpenStreetMap contributors, Overture Maps Foundation |
| Overture Maps Foundation, `places`, release 2026-10-21.0 | Refuges, relief stores and candidate public buildings | CDLA Permissive 2.0 (Meta, Microsoft), Apache 2.0 (Foursquare), CC0 (AllThePlaces) | Overture Maps Foundation, with data from Meta, Microsoft, Foursquare and AllThePlaces |
| Meta and CIESIN – Columbia University, High Resolution Settlement Layer (general population and people aged 60+) | Population per hexagon | CC BY 4.0 | Meta and CIESIN – Columbia University, High Resolution Settlement Layer |

**Why ODbL:** the walking times are computed on Overture's transportation network, which is ODbL.
ODbL's share-alike clause asks that a publicly used derivative database stays under ODbL. The other
sources are permissive; population values keep the CC BY 4.0 attribution above.

**Not stored here:** results from Amazon Location Service (geocoding, nearby places, routes and
isolines) are requested live by the web app and are never saved in this repository.
