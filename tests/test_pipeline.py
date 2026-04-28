# tests/test_pipeline.py

import pytest
from geordie import Geordie

SAMPLE_TEXTS = [
    "This study analyses coastal vulnerability in the Ebro Delta and applies the model to Barcelona.",
    "The conference was held in Paris and the results were applied to French coastal regions.",
    "Research conducted at the University of Bologna focused on Italian biodiversity.",
]

@pytest.fixture(scope="module")
def geordie_nominatim():
    """Full pipeline with Nominatim — loaded once for all tests in this module."""
    return Geordie(linker_backend="nominatim")

@pytest.fixture(scope="module")
def geordie_geonames():
    """Full pipeline with GeoNames — loaded once for all tests in this module."""
    return Geordie(linker_backend="geonames", dump="cities15000")


class TestPipelineNominatim:

    def test_process_text_returns_list(self, geordie_nominatim):
        results = geordie_nominatim.process_text(SAMPLE_TEXTS[0])
        assert isinstance(results, list)

    def test_process_text_has_required_keys(self, geordie_nominatim):
        results = geordie_nominatim.process_text(SAMPLE_TEXTS[0])
        assert len(results) > 0
        for item in results:
            assert "entity" in item
            assert "entity_normalised" in item
            assert "context" in item
            assert "geo" in item
            assert "role" in item
            assert "role_label" in item

    def test_entity_markers_in_context(self, geordie_nominatim):
        results = geordie_nominatim.process_text(SAMPLE_TEXTS[0])
        for item in results:
            assert "[START_ENT]" in item["context"]
            assert "[END_ENT]" in item["context"]

    def test_geo_is_dict(self, geordie_nominatim):
        results = geordie_nominatim.process_text(SAMPLE_TEXTS[0])
        for item in results:
            assert isinstance(item["geo"], dict)

    def test_role_label_is_valid(self, geordie_nominatim):
        from geordie.role_classification import GeoRole
        results = geordie_nominatim.process_text(SAMPLE_TEXTS[0])
        valid_roles = {r.value for r in GeoRole} | {None}
        for item in results:
            assert item["role_label"] in valid_roles or isinstance(item["role_label"], str)

    def test_normaliser_applied(self, geordie_nominatim):
        results = geordie_nominatim.process_text(
            "French coastal erosion has been studied extensively."
        )
        normalised = [r["entity_normalised"] for r in results]
        assert "France" in normalised

    def test_process_corpus(self, geordie_nominatim):
        results = geordie_nominatim.process_corpus(SAMPLE_TEXTS)
        assert len(results) == len(SAMPLE_TEXTS)
        for doc_results in results:
            assert isinstance(doc_results, list)

    def test_empty_text(self, geordie_nominatim):
        results = geordie_nominatim.process_text("No geographic entities here.")
        assert isinstance(results, list)


class TestPipelineGeoNames:

    def test_process_text_geonames(self, geordie_geonames):
        results = geordie_geonames.process_text(SAMPLE_TEXTS[0])
        assert isinstance(results, list)
        assert len(results) > 0

    def test_geo_has_geonames_fields(self, geordie_geonames):
        results = geordie_geonames.process_text(
            "The study was conducted in Barcelona, Spain."
        )
        geo_results = [r for r in results if r["geo"]]
        assert len(geo_results) > 0
        for item in geo_results:
            assert "geonameid" in item["geo"]
            assert "source" in item["geo"]
            assert item["geo"]["source"] == "geonames_local"
            assert isinstance(item["geo"]["lat"], float)
            assert isinstance(item["geo"]["lon"], float)

    def test_match_type_present(self, geordie_geonames):
        results = geordie_geonames.process_text(
            "Research in Madrid focused on urban heat islands."
        )
        geo_results = [r for r in results if r["geo"]]
        for item in geo_results:
            assert item["geo"]["match_type"] in ("exact", "fuzzy")