"""City configuration. Add a city by giving it a bounding box and either:
  - "locality": the name of its Overture `locality` polygon (used as the urban study area), or
  - "county": the name of its municipality polygon, when Overture has no locality for the city. The
    study area is then the city's urban footprint, derived from population (build.urban_footprint)."""

OVERTURE_RELEASE = "2026-10-21.0"
HRSL_VERSION = "latest"  # Meta High Resolution Population Density Maps (Registry of Open Data on AWS)

CITIES = {
    "culiacan": {
        "name": "Culiacán",
        "state": "Sinaloa",
        "bbox": (-107.55, 24.68, -107.28, 24.90),  # xmin, ymin, xmax, ymax
        "locality": "Culiacán Rosales",
        "center": (-107.394, 24.799),
        "zoom": 12.2,
    },
    "hermosillo": {
        "name": "Hermosillo",
        "state": "Sonora",
        "bbox": (-111.12, 28.95, -110.85, 29.20),
        "county": "Hermosillo",
        "center": (-110.961, 29.073),
        "zoom": 11.8,
    },
    "mexicali": {
        "name": "Mexicali",
        "state": "Baja California",
        "bbox": (-115.62, 32.50, -115.25, 32.68),
        "county": "Municipio de Mexicali",
        "center": (-115.455, 32.615),
        "zoom": 11.6,
    },
}

# Walking model
WALK_SPEED_MS = 1.0          # 3.6 km/h: a conservative pace for older adults in heat
THRESHOLDS_MIN = (5, 10, 15)  # access bands shown on the map
COVER_MIN = 10                # "covered" = a refuge within this many minutes on foot
N_PROPOSALS = 10              # new refuges to propose per city
H3_RES = 10                   # ~0.015 km2 hexagons (edge ~66 m)
MAX_SNAP_M = 400              # hexagons farther than this from any street are dropped
