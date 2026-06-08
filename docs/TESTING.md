# GEORDIE — Testing Guide

## Prerequisites

All dependencies confirmed working:

```
torch:        2.10.0+cu128
transformers: 5.2.0
nltk:         3.9.3
geopy:        2.4.1
pytest:       9.0.2
pytest-cov:   7.0.0
```

Always run pytest through the venv Python:

```bash
python -m pytest ...   # correct
pytest ...             # wrong — picks up system Python
```

---

## Test layers

### Layer 1 — Unit tests (no network, no models)

Tests cache, normaliser, GeoNames linker, and download logic using synthetic data.

```bash
python -m pytest tests/ -v --ignore=tests/test_nominatim_live.py --ignore=tests/test_pipeline.py
```

| Test file | What it covers |
|---|---|
| `test_cache.py` | `SQLiteCache` set/get/TTL/eviction/clear |
| `test_normaliser.py` | demonym and adjective normalisation |
| `test_linkers.py` | `get_cache_dir`, `default_cache_path`, context manager, stats, confirmed miss |
| `test_geonames.py` | exact match, case insensitivity, alternate names, fuzzy, miss, scoring, cache |
| `test_download.py` | auto-download, skip-if-cached, auto-download via `GeoNamesLinker` |

---

### Layer 2 — Live Nominatim (network required)

Hits the real OpenStreetMap Nominatim API. Slow due to 1.1s rate-limit sleep between calls.

```bash
python -m pytest tests/test_nominatim_live.py -v -s
```

| Test | What it checks |
|---|---|
| `test_nominatim_barcelona` | real geocoding, `lat`/`lon` as float, `osm_class`, `address_type` |
| `test_nominatim_caches_hit` | second call returns cached result |
| `test_nominatim_miss` | unknown entity returns `None` |

---

### Layer 3 — Full pipeline (models required)

Downloads `SIRIS-Lab/geordie-ner` and `SIRIS-Lab/geordie-role` from HuggingFace on first run (~500 MB).
Models are cached in `~/.cache/huggingface/hub/` — subsequent runs are fast.

#### Pre-fetch models manually (optional)

```bash
python - << 'EOF'
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import AutoModelForSequenceClassification

print("Downloading NER model...")
AutoTokenizer.from_pretrained("SIRIS-Lab/geordie-ner")
AutoModelForTokenClassification.from_pretrained("SIRIS-Lab/geordie-ner")

print("Downloading role classifier...")
AutoTokenizer.from_pretrained("SIRIS-Lab/geordie-role")
AutoModelForSequenceClassification.from_pretrained("SIRIS-Lab/geordie-role")

print("Done — both models cached.")
EOF
```

#### Run pipeline tests

```bash
python -m pytest tests/test_pipeline.py -v -s
```

| Test class | Backend | What it checks |
|---|---|---|
| `TestPipelineNominatim` | Nominatim | output keys, entity markers, geo dict, role labels, normalisation, corpus, empty text |
| `TestPipelineGeoNames` | GeoNames | same + `geonameid`, `source`, float coords, `match_type` |

---

### Full suite with coverage

```bash
python -m pytest tests/ -v --cov=geordie --cov-report=term-missing
```

#### Coverage baseline (without pipeline tests)

| File | Cover |
|---|---|
| `demonyms_and_adjectives.py` | 100% |
| `utils/__init__.py` | 100% |
| `resources/__init__.py` | 100% |
| `normaliser.py` | 83% |
| `geonames.py` | 90% |
| `nominatim.py` | 74% |
| `base.py` | 75% |
| `download.py` | 43% |
| `__init__.py` | 21% |
| `ner.py` | 0% |
| `role_classification.py` | 0% |
| `cli.py` | 0% |
| **TOTAL** | **59%** |

#### Expected after pipeline tests

| File | Expected |
|---|---|
| `__init__.py` | ~85% |
| `ner.py` | ~90% |
| `role_classification.py` | ~85% |
| **TOTAL** | **~80%+** |

---

## Fix for `ResourceWarning: unclosed database`

Add `__del__` to `BaseLinker` in `geordie/linkers/base.py`:

```python
def __del__(self):
    """Close the SQLite cache connection on garbage collection."""
    if isinstance(self._cache, SQLiteCache):
        try:
            self._cache.close()
        except Exception:
            pass
```

And use a pytest fixture in `test_geonames.py` to ensure explicit teardown:

```python
@pytest.fixture
def linker(tmp_path):
    geonames_file = tmp_path / "test_cities.txt"
    geonames_file.write_text(SAMPLE_TSV, encoding="utf-8")
    lnk = GeoNamesLinker(
        geonames_path=geonames_file,
        cache_path=tmp_path / "test_cache.db",
    )
    yield lnk
    lnk._cache.close()   # explicit teardown after every test
```

---

## Cache locations

```
~/.cache/geordie/
├── nominatim.db               ← Nominatim SQLite cache
├── geonames.db                ← GeoNames SQLite cache
└── geonames/
    └── cities15000.txt        ← auto-downloaded GeoNames dump
```

Override with environment variables:

```bash
export GEORDIE_CACHE=/path/to/custom/cache
# or
export XDG_CACHE_HOME=/path/to/xdg/cache
```

---

## Quick reference

```bash
# Fast only (no network, no models)
python -m pytest tests/test_cache.py tests/test_normaliser.py tests/test_geonames.py tests/test_linkers.py -v

# Without pipeline tests
python -m pytest tests/ -v --ignore=tests/test_nominatim_live.py --ignore=tests/test_pipeline.py

# With Nominatim (network)
python -m pytest tests/ -v --ignore=tests/test_pipeline.py

# Full suite including models
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ -v --cov=geordie --cov-report=term-missing

# HTML coverage report
python -m pytest tests/ -v --cov=geordie --cov-report=html
# open htmlcov/index.html
```