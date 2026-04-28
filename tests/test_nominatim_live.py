# tests/test_nominatim_live.py
# Run explicitly: pytest tests/test_nominatim_live.py -v -s

import tempfile
import pytest
from geordie.linkers.nominatim import NominatimLinker

@pytest.mark.slow
def test_nominatim_barcelona(tmp_path):
    linker = NominatimLinker(cache_path=tmp_path / "nom.db")
    result = linker._lookup("Barcelona")
    assert result is not None
    assert result["country_code"] == "es"
    assert isinstance(result["lat"], float)
    assert result["osm_class"] is not None   # e.g. "boundary"
    assert result["address_type"] is not None  # e.g. "city"

@pytest.mark.slow
def test_nominatim_caches_hit(tmp_path):
    linker = NominatimLinker(cache_path=tmp_path / "nom.db")
    r1 = linker._lookup("Paris")
    r2 = linker._lookup("Paris")  # should hit cache, no API call
    assert r1 == r2

@pytest.mark.slow
def test_nominatim_miss(tmp_path):
    linker = NominatimLinker(cache_path=tmp_path / "nom.db")
    result = linker._lookup("Zzzznotacity99999")
    assert result is None