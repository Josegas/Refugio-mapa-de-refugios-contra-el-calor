"""Unit tests for the place rules: what counts as a refuge, a relief store, or a candidate public building.

These run in a fraction of a second and need no data files, so they always run (also in CI).
"""
import pytest

from build import candidate_type, classify


@pytest.mark.parametrize("name, cat, expected", [
    # Relief stores ("alivio"): air-conditioned shops where you buy water
    ("OXXO Las Quintas", "convenience_store", ("alivio", "conveniencia")),
    ("Farmacias Similares", "pharmacy", ("alivio", "farmacia")),
    # Refuges: you can stay without buying anything
    ("Casa Ley Humaya", "supermarket", ("refugio", "super")),
    ("Biblioteca Pública Gilberto Owen", "library", ("refugio", "biblioteca")),
    ("DIF Municipal Culiacán", "social_or_community_service", ("refugio", "comunitario")),
    # Category noise found in Overture (see docs/journal.md, 14:15): must be excluded
    ("BanCoppel", "shopping_mall", None),
    ("Centro Penitenciario de Aguaruto", "community_center", None),
    ("Panteón Civil San Juan", "community_center", None),
    # A random grocery store that is not a big supermarket brand is not a refuge
    ("Abarrotes Doña Mary", "grocery_store", None),
    # Manual curation (journal 19:30): businesses and groups mislabeled as malls or centers
    ("Maxi Tours", "shopping_mall", None),
    ("Megacable Universitarios", "shopping_mall", None),
    ("Temazcal Colibrí Culiacán", "community_center", None),
    ("Movimiento Gnóstico Culiacán", "cultural_center", None),
    # ...but real malls and cultural centers stay
    ("Plaza Fiesta Culiacán", "shopping_mall", ("refugio", "plaza")),
    ("Casa de la Cultura Miguel Tamayo", "cultural_center", ("refugio", "cultura")),
])
def test_classify(name, cat, expected):
    assert classify(name, cat) == expected


@pytest.mark.parametrize("name, cat, expected", [
    # Public buildings are valid candidates
    ("Escuela Primaria Benito Juárez", "elementary_school", "escuela"),
    ("CBTIS 43", "high_school", "escuela"),
    ("Sindicatura de Costa Rica", "government_office", "gobierno"),
    ("Unidad Deportiva Juan S. Millán", "sports_and_recreation", "deportivo"),
    # Private schools, daycares and clubs are not (journal 14:29: the first run proposed these)
    ("Instituto Cumbres Culiacán", "school", None),
    ("Colegio Chapultepec", "elementary_school", None),
    ("Estancia Infantil Pasitos", "preschool", None),
    ("Club Deportivo Tres Ríos", "sports_and_recreation", None),
    # A "school" whose name doesn't look like a public school is not trusted
    ("Little Genius Kids", "school", None),
    # Temples are no longer candidates
    ("Parroquia San Judas Tadeo", "roman_catholic_place_of_worship", None),
    # Noise in Overture's government/social/sports categories (second run, journal 15:55)
    ("Udeci, A.C.", "social_or_community_service", None),          # civil association = private
    ("Unidas Por La Paz, Iap", "social_or_community_service", None),
    ("INE Sinaloa", "social_or_community_service", None),          # federal office, not a refuge site
    ("UltraGym & Fitness", "sports_and_recreation", None),
    ("Penal de Aguaruto", "social_or_community_service", None),
    ("Centros Comunitarios Rosa", "sports_and_recreation", "deportivo"),
])
def test_candidate_type(name, cat, expected):
    assert candidate_type(name, cat) == expected
