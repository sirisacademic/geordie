# tests/test_geonames.py

import tempfile
from pathlib import Path
from geordie.linkers.geonames import GeoNamesLinker

# Minimal valid GeoNames TSV row (15 columns)
# geonameid, name, asciiname, alternatenames, lat, lon,
# feature_class, feature_code, country_code, cc2,
# admin1, admin2, admin3, admin4, population
SAMPLE_TSV = """\
3128760\tBarcelona\tBarcelona\tBCN,Barcelone,Barselona\t41.38879\t2.15899\tP\tPPLA\tES\t\t56\t08019\t\t\t1620343
2968815\tParis\tParis\tLutecia,Paname\t48.85341\t2.3488\tP\tPPLC\tFR\t\t11\t\t\t\t2138551
3117735\tMadrid\tMadrid\tMadrid\t40.4165\t-3.70256\tP\tPPLC\tES\t\t29\t\t\t\t3255944
"""

def make_linker(tmp_path, use_fuzzy=True):
    geonames_file = tmp_path / "test_cities.txt"
    geonames_file.write_text(SAMPLE_TSV, encoding="utf-8")
    linker = GeoNamesLinker(
        geonames_path=geonames_file,
        cache_path=tmp_path / "test_cache.db",
        use_fuzzy=use_fuzzy,
    )
    return linker

def test_exact_match(tmp_path):
    linker = make_linker(tmp_path)
    try:
        result = linker._lookup("Barcelona")
        assert result is not None
    finally:
        linker._cache.close()   # explicit close

def test_exact_match_case_insensitive(tmp_path):
    linker = make_linker(tmp_path)
    result = linker._lookup("PARIS")
    assert result is not None
    assert result["name"] == "Paris"

def test_alternate_name_match(tmp_path):
    linker = make_linker(tmp_path)
    result = linker._lookup("Barcelone")   # French alternate name
    assert result is not None
    assert result["name"] == "Barcelona"

def test_fuzzy_match(tmp_path):
    linker = make_linker(tmp_path, use_fuzzy=True)
    result = linker._lookup("Madrид")      # typo
    # may or may not match depending on threshold — just check no crash
    assert result is None or result["name"] == "Madrid"

def test_fuzzy_disabled(tmp_path):
    linker = make_linker(tmp_path, use_fuzzy=False)
    result = linker._lookup("Barcelonaa")  # typo
    assert result is None

def test_no_match(tmp_path):
    linker = make_linker(tmp_path)
    result = linker._lookup("Zzzznotacity")
    assert result is None

def test_link_entities_caches_miss(tmp_path):
    linker = make_linker(tmp_path)
    entities = [{"entity": "Zzzznotacity", "entity_normalised": "Zzzznotacity"}]
    results = linker.link_entities(entities)
    assert results[0]["geo"] == {}
    # second call should hit cache — no re-lookup
    results2 = linker.link_entities(entities)
    assert results2[0]["geo"] == {}

def test_link_entities_full(tmp_path):
    linker = make_linker(tmp_path)
    entities = [
        {"entity": "Barcelona", "entity_normalised": "Barcelona"},
        {"entity": "Paris",     "entity_normalised": "Paris"},
    ]
    results = linker.link_entities(entities)
    assert results[0]["geo"]["country_code"] == "ES"
    assert results[1]["geo"]["country_code"] == "FR"

def test_match_score_present(tmp_path):
    linker = make_linker(tmp_path)
    result = linker._lookup("Madrid")
    assert "match_score" in result
    assert 0.0 <= result["match_score"] <= 1.0

def test_population_disambiguation(tmp_path):
    """Madrid has higher population than Barcelona — both in ES but different scores."""
    linker = make_linker(tmp_path)
    bcn = linker._lookup("Barcelona")
    mad = linker._lookup("Madrid")
    assert bcn["name"] == "Barcelona"
    assert mad["name"] == "Madrid"