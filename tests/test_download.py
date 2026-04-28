# tests/test_download.py

import pytest
from geordie.utils.download import download_geonames_dump, get_geonames_cache_dir

@pytest.mark.slow
def test_download_cities15000():
    path = download_geonames_dump("cities15000")
    assert path.exists()
    assert path.suffix == ".txt"
    assert path.stat().st_size > 1_000_000   # at least 1 MB

@pytest.mark.slow
def test_download_skips_if_cached():
    path1 = download_geonames_dump("cities15000")
    path2 = download_geonames_dump("cities15000")  # should skip
    assert path1 == path2

@pytest.mark.slow
def test_geonames_linker_auto_download():
    from geordie.linkers.geonames import GeoNamesLinker
    linker = GeoNamesLinker(dump="cities15000")   # no path — auto-downloads
    result = linker._lookup("Barcelona")
    assert result is not None
    assert result["country_code"] == "ES"