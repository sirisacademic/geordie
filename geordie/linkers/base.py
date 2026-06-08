"""Abstract base class and SQLite cache for entity linkers."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cache directory resolution  (mirrors HuggingFace / NLTK convention)
# ---------------------------------------------------------------------------

def get_cache_dir() -> Path:
    """
    Return the geordie cache directory, creating it if necessary.

    Resolution order:
    1. ``GEORDIE_CACHE`` environment variable (full override)
    2. ``XDG_CACHE_HOME`` / geordie           (Linux standard)
    3. ``~/.cache/geordie``                   (fallback, same as HuggingFace)
    """
    if "GEORDIE_CACHE" in os.environ:
        cache_dir = Path(os.environ["GEORDIE_CACHE"])
    elif "XDG_CACHE_HOME" in os.environ:
        cache_dir = Path(os.environ["XDG_CACHE_HOME"]) / "geordie"
    else:
        cache_dir = Path.home() / ".cache" / "geordie"

    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def default_cache_path(filename: str = "geordie_cache.db") -> Path:
    """Return the default path for a named cache file inside the geordie cache dir."""
    return get_cache_dir() / filename


# ---------------------------------------------------------------------------
# SQLiteCache
# ---------------------------------------------------------------------------

class SQLiteCache:
    """
    Persistent SQLite-backed cache with optional TTL and LRU-based eviction.

    The database is stored under ``~/.cache/geordie/`` by default (same
    convention as HuggingFace Hub and NLTK).  Override via the
    ``GEORDIE_CACHE`` or ``XDG_CACHE_HOME`` environment variables.

    Supports use as a context manager::

        with SQLiteCache() as cache:
            cache.set("Barcelona", {"lat": 41.38, "lon": 2.17})
            result = cache.get("Barcelona")

    Parameters
    ----------
    db_path :
        Path to the SQLite file.  Defaults to
        ``~/.cache/geordie/geordie_cache.db``.
    table :
        Table name inside the SQLite database (useful for namespacing
        multiple linkers in one file).
    maxsize :
        Maximum number of entries before LRU eviction kicks in.
    ttl :
        Time-to-live in seconds.  ``None`` means entries never expire.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        table: str = "cache",
        maxsize: int = 50_000,
        ttl: float | None = None,
    ):
        if db_path is None:
            db_path = default_cache_path()
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)  # ensure dir exists
        self.table = table
        self.maxsize = maxsize
        self.ttl = ttl
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._create_table()
        logger.debug("SQLiteCache opened: %s (table=%s)", self.db_path, self.table)

    def _create_table(self) -> None:
        self._conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table} (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                created_at REAL NOT NULL,
                last_used  REAL NOT NULL
            )
        """)
        # Index on last_used — makes LRU eviction O(log n) instead of full sort
        self._conn.execute(f"""
            CREATE INDEX IF NOT EXISTS {self.table}_lru
            ON {self.table} (last_used ASC)
        """)
        # Index on created_at — makes TTL expiry scan fast
        self._conn.execute(f"""
            CREATE INDEX IF NOT EXISTS {self.table}_ttl
            ON {self.table} (created_at ASC)
        """)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def get(self, key: str) -> dict | None:
        """
        Return the cached value for *key*, or ``None`` on miss / expiry.

        Note: ``{}`` (empty dict) is a valid cached value — it represents a
        confirmed lookup miss, cached to avoid redundant API calls.
        """
        row = self._conn.execute(
            f"SELECT value, created_at FROM {self.table} WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        value_json, created_at = row
        if self.ttl is not None and (time.time() - created_at) > self.ttl:
            self._conn.execute(f"DELETE FROM {self.table} WHERE key = ?", (key,))
            self._conn.commit()
            return None
        self._conn.execute(
            f"UPDATE {self.table} SET last_used = ? WHERE key = ?",
            (time.time(), key),
        )
        self._conn.commit()
        return json.loads(value_json)

    def set(self, key: str, value: Any) -> None:
        """Store *value* under *key*, evicting oldest entries if over *maxsize*."""
        now = time.time()
        self._conn.execute(
            f"""INSERT OR REPLACE INTO {self.table} (key, value, created_at, last_used)
                VALUES (?, ?, ?, ?)""",
            (key, json.dumps(value, ensure_ascii=False), now, now),
        )
        self._conn.commit()
        self._evict_if_needed()

    def _evict_if_needed(self) -> None:
        count = self._conn.execute(
            f"SELECT COUNT(*) FROM {self.table}"
        ).fetchone()[0]
        if count > self.maxsize:
            excess = count - self.maxsize
            self._conn.execute(
                f"DELETE FROM {self.table} WHERE key IN "
                f"(SELECT key FROM {self.table} ORDER BY last_used ASC LIMIT ?)",
                (excess,),
            )
            self._conn.commit()

    def expire_stale(self) -> int:
        """Delete all TTL-expired entries. Returns number of rows removed."""
        if self.ttl is None:
            return 0
        cutoff = time.time() - self.ttl
        cur = self._conn.execute(
            f"DELETE FROM {self.table} WHERE created_at < ?", (cutoff,)
        )
        self._conn.commit()
        return cur.rowcount

    def clear(self) -> None:
        """Remove all entries from the cache table."""
        self._conn.execute(f"DELETE FROM {self.table}")
        self._conn.commit()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Current number of entries in the cache."""
        return self._conn.execute(
            f"SELECT COUNT(*) FROM {self.table}"
        ).fetchone()[0]

    def stats(self) -> dict:
        """
        Return a summary dict — useful for debugging and monitoring.

        Example output::

            {
                "db_path": "/home/user/.cache/geordie/geordie_nominatim_cache.db",
                "table": "cache",
                "size": 1234,
                "maxsize": 50000,
                "ttl": 2592000,
                "oldest_created": 1710000000.0,
                "latest_used": 1712345678.9,
            }
        """
        row = self._conn.execute(
            f"SELECT COUNT(*), MIN(created_at), MAX(last_used) FROM {self.table}"
        ).fetchone()
        count, oldest_created, latest_used = row
        return {
            "db_path": str(self.db_path),
            "table": self.table,
            "size": count,
            "maxsize": self.maxsize,
            "ttl": self.ttl,
            "oldest_created": oldest_created,
            "latest_used": latest_used,
        }

    # ------------------------------------------------------------------
    # Context manager + repr
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()

    def __enter__(self) -> "SQLiteCache":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            f"SQLiteCache(db_path={str(self.db_path)!r}, "
            f"table={self.table!r}, size={self.size}/{self.maxsize}, ttl={self.ttl})"
        )


# ---------------------------------------------------------------------------
# BaseLinker
# ---------------------------------------------------------------------------

class BaseLinker(ABC):
    """
    Abstract base for geographic entity linkers.

    Subclasses must implement:
    - ``_lookup(entity: str) -> dict | None``
    - ``_make_key(entity: str) -> str``
    """

    def __init__(
        self,
        cache_path: str | Path | None = None,
        cache_maxsize: int = 50_000,
        cache_ttl: float | None = None,
        sleep_between_calls: float = 0.0,
    ):
        self._sleep = sleep_between_calls
        if cache_path is not None:
            self._cache: SQLiteCache | dict = SQLiteCache(
                db_path=cache_path, maxsize=cache_maxsize, ttl=cache_ttl
            )
        else:
            self._cache = {}
        self._logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def _lookup(self, entity: str) -> dict | None: ...

    @abstractmethod
    def _make_key(self, entity: str) -> str: ...

    def _cache_get(self, key: str) -> dict | None:
        if isinstance(self._cache, SQLiteCache):
            return self._cache.get(key)
        return self._cache.get(key)

    def _cache_set(self, key: str, value: dict | None) -> None:
        stored = value if value is not None else {}
        if isinstance(self._cache, SQLiteCache):
            self._cache.set(key, stored)
        else:
            self._cache[key] = stored

    def __del__(self):
        """Close the SQLite cache connection on garbage collection."""
        if isinstance(self._cache, SQLiteCache):
            try:
                self._cache.close()
            except Exception:
                pass

    def clear_cache(self) -> None:
        if isinstance(self._cache, SQLiteCache):
            self._cache.clear()
        else:
            self._cache.clear()

    def cache_stats(self) -> dict:
        """Return cache statistics (backend, size, path)."""
        if isinstance(self._cache, SQLiteCache):
            return {"backend": "sqlite", **self._cache.stats()}
        return {"backend": "memory", "size": len(self._cache), "maxsize": None}

    

    def link_entities(self, entities: list[dict]) -> list[dict]:
        results = []
        for item in entities:
            entity = item.get("entity_normalised") or item.get("entity") or ""
            key = self._make_key(entity)

            cached = self._cache_get(key)
            if cached is not None:
                item["geo"] = cached
                results.append(item)
                continue

            try:
                result = self._lookup(entity)
            except Exception as exc:
                self._logger.warning("Lookup error for %r: %s", entity, exc)
                result = None

            self._cache_set(key, result)
            item["geo"] = result if result else {}
            results.append(item)

            if self._sleep:
                time.sleep(self._sleep)

        return results