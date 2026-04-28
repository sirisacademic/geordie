# tests/test_linkers.py

import tempfile
from pathlib import Path
from geordie.linkers.base import SQLiteCache, default_cache_path, get_cache_dir

def test_cache_dir():
    d = get_cache_dir()
    assert d.exists()
    assert d.name == "geordie"

def test_default_cache_path():
    p = default_cache_path("test.db")
    assert p.name == "test.db"
    assert "geordie" in str(p)

def test_cache_context_manager():
    with tempfile.TemporaryDirectory() as tmpdir:
        with SQLiteCache(db_path=Path(tmpdir) / "t.db") as cache:
            cache.set("Barcelona", {"lat": 41.38, "lon": 2.17})
            result = cache.get("Barcelona")
            assert result["lat"] == 41.38

def test_cache_stats():
    with tempfile.TemporaryDirectory() as tmpdir:
        with SQLiteCache(db_path=Path(tmpdir) / "t.db") as cache:
            cache.set("Paris", {"lat": 48.85})
            stats = cache.stats()
            assert stats["size"] == 1
            assert "db_path" in stats

def test_cache_confirmed_miss():
    """Empty dict {} is a valid cached value (confirmed API miss)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with SQLiteCache(db_path=Path(tmpdir) / "t.db") as cache:
            cache.set("xyz_unknown", {})
            result = cache.get("xyz_unknown")
            assert result == {}   # not None — miss is cached