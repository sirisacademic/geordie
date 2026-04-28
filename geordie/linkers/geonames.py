"""GeoNames local entity linker — offline-first, no API calls."""

from __future__ import annotations

import csv
import difflib
import logging
import math
from pathlib import Path

from .base import BaseLinker, default_cache_path
from ..utils.download import download_geonames_dump

logger = logging.getLogger(__name__)

COL_GEONAMEID      = 0
COL_NAME           = 1
COL_ASCIINAME      = 2
COL_ALTERNATENAMES = 3
COL_LATITUDE       = 4
COL_LONGITUDE      = 5
COL_FEATURE_CLASS  = 6
COL_FEATURE_CODE   = 7
COL_COUNTRY_CODE   = 8
COL_ADMIN1         = 10
COL_ADMIN2         = 11
COL_POPULATION     = 14

_FEATURE_PRIORITY: dict[str, int] = {"P": 0, "A": 1, "T": 2, "H": 2}


def _normalise(s: str) -> str:
    return s.strip().lower()


def _make_trigrams(s: str) -> set[str]:
    padded = f"  {s}  "
    return {padded[i:i+3] for i in range(len(padded) - 2)}


class GeoNamesLinker(BaseLinker):
    """
    Entity linker using a local GeoNames gazetteer dump (TSV).

    Auto-downloads the dump to ``~/.cache/geordie/geonames/`` on first use
    if ``geonames_path`` is not provided.

    Parameters
    ----------
    geonames_path :
        Path to a GeoNames ``.txt`` file. If ``None``, auto-downloaded.
    dump :
        Which dump to download if ``geonames_path`` is None.
        One of ``"cities500"``, ``"cities1000"``, ``"cities5000"``,
        ``"cities15000"`` (default), ``"allCountries"``.
    force_download :
        Re-download even if already cached.
    cache_path :
        SQLite cache. Defaults to ``~/.cache/geordie/geonames.db``.
    cache_maxsize :
        Max SQLite cache entries before LRU eviction.
    cache_ttl :
        Cache TTL in seconds (``None`` = never expire).
    min_population :
        Skip entries below this population.
    feature_classes :
        GeoNames feature classes to index. Default: ``{"P", "A"}``.
    use_fuzzy :
        Fall back to trigram + difflib reranking on exact miss.
    fuzzy_threshold :
        Minimum similarity score (0–1) to accept a fuzzy match.
    max_fuzzy_candidates :
        Number of trigram candidates to rerank.
    """

    def __init__(
        self,
        geonames_path: str | Path | None = None,
        dump: str = "cities15000",
        force_download: bool = False,
        cache_path: str | Path | None = None,
        cache_maxsize: int = 100_000,
        cache_ttl: float | None = None,
        min_population: int = 0,
        feature_classes: set[str] | None = None,
        use_fuzzy: bool = True,
        fuzzy_threshold: float = 0.65,
        max_fuzzy_candidates: int = 10,
    ):
        super().__init__(
            cache_path=cache_path or default_cache_path("geonames.db"),
            cache_maxsize=cache_maxsize,
            cache_ttl=cache_ttl,
            sleep_between_calls=0.0,
        )

        if geonames_path is None:
            geonames_path = download_geonames_dump(dump=dump, force=force_download)
        else:
            geonames_path = Path(geonames_path)
            if not geonames_path.exists():
                raise FileNotFoundError(
                    f"GeoNames file not found: {geonames_path}\n"
                    "Tip: omit geonames_path to auto-download."
                )

        self.geonames_path = Path(geonames_path)
        self.dump_name = Path(geonames_path).stem   # e.g. "allCountries", "cities15000"
        self.min_population = min_population
        self.feature_classes = feature_classes or {"P", "A", "T", "H"}
        self.use_fuzzy = use_fuzzy
        self.fuzzy_threshold = fuzzy_threshold
        self.max_fuzzy_candidates = max_fuzzy_candidates

        self._index: dict[str, list[dict]] = {}
        self._trigram_index: dict[str, set[str]] = {}

        # Purge stale cache entries that were written without the dump-name prefix
        # (i.e. from geordie versions before this fix).  One-time migration.
        self._migrate_legacy_cache_keys()
        self._load_index()

    def _migrate_legacy_cache_keys(self) -> None:
        """
        One-time migration: delete old cache entries that were written with the
        legacy key format ``gn|<entity>`` (no dump name).  Those entries are
        shared across dumps and can serve wrong results.
        """
        from .base import SQLiteCache
        if not isinstance(self._cache, SQLiteCache):
            return
        # Legacy keys start with "gn|" but do NOT contain a second "|"
        deleted = self._cache._conn.execute(
            "DELETE FROM cache WHERE key LIKE 'gn|%' AND key NOT LIKE 'gn|%|%'"
        ).rowcount
        self._cache._conn.commit()
        if deleted:
            logger.info(
                "Migrated GeoNames cache: removed %d legacy entries (no dump-name prefix).",
                deleted,
            )

    def clear_cache_for_dump(self) -> None:
        """Clear only the cache entries that belong to this dump (non-destructive)."""
        from .base import SQLiteCache
        if not isinstance(self._cache, SQLiteCache):
            self._cache.clear()
            return
        prefix = f"gn|{self.dump_name}|"
        deleted = self._cache._conn.execute(
            "DELETE FROM cache WHERE key LIKE ?", (prefix + "%",)
        ).rowcount
        self._cache._conn.commit()
        logger.info("Cleared %d cache entries for dump %r.", deleted, self.dump_name)

    def _load_index(self) -> None:
        logger.info("Loading GeoNames index from %s ...", self.geonames_path)
        count = 0

        with open(self.geonames_path, encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
            for row in reader:
                if len(row) < 15:
                    continue
                feature_class = row[COL_FEATURE_CLASS]
                if feature_class not in self.feature_classes:
                    continue
                try:
                    population = int(row[COL_POPULATION]) if row[COL_POPULATION] else 0
                except ValueError:
                    population = 0
                if population < self.min_population:
                    continue

                try:
                    lat = float(row[COL_LATITUDE])
                    lon = float(row[COL_LONGITUDE])
                except ValueError:
                    lat, lon = 0.0, 0.0

                entry = {
                    "geonameid":     row[COL_GEONAMEID],
                    "name":          row[COL_NAME],
                    "asciiname":     row[COL_ASCIINAME],
                    "lat":           lat,
                    "lon":           lon,
                    "feature_class": feature_class,
                    "feature_code":  row[COL_FEATURE_CODE],
                    "country_code":  row[COL_COUNTRY_CODE],
                    "admin1":        row[COL_ADMIN1],
                    "admin2":        row[COL_ADMIN2] if len(row) > COL_ADMIN2 else "",
                    "population":    population,
                }

                name_keys: set[str] = {
                    _normalise(row[COL_NAME]),
                    _normalise(row[COL_ASCIINAME]),
                }
                if row[COL_ALTERNATENAMES]:
                    for alt in row[COL_ALTERNATENAMES].split(","):
                        key = _normalise(alt)
                        if key:
                            name_keys.add(key)

                for key in name_keys:
                    self._index.setdefault(key, []).append(entry)
                    if self.use_fuzzy:
                        for trigram in _make_trigrams(key):
                            self._trigram_index.setdefault(trigram, set()).add(key)

                count += 1

        logger.info(
            "GeoNames index loaded: %d entries, %d name keys, %d trigrams",
            count, len(self._index), len(self._trigram_index),
        )

    def _make_key(self, entity: str) -> str:
        # Include dump name so cities15000 and allCountries never share cache entries.
        return f"gn|{self.dump_name}|{_normalise(entity)}"

    def _lookup(self, entity: str) -> dict | None:
        norm = _normalise(entity)

        candidates = self._index.get(norm)
        if candidates:
            return self._best(candidates, match_type="exact", query=norm)

        if self.use_fuzzy:
            return self._fuzzy_lookup(norm)

        return None

    def _best(self, candidates: list[dict], match_type: str, query: str) -> dict:
        scored = []
        for c in candidates:
            sim   = difflib.SequenceMatcher(None, query, _normalise(c["name"])).ratio()
            pop   = math.log1p(c["population"]) / 20
            prio  = 1.0 - _FEATURE_PRIORITY.get(c["feature_class"], 2) * 0.1
            score = sim * 0.6 + pop * 0.3 + prio * 0.1
            scored.append((score, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best = scored[0]

        return {
            "geonameid":     best["geonameid"],
            "name":          best["name"],
            "lat":           best["lat"],
            "lon":           best["lon"],
            "country_code":  best["country_code"],
            "feature_class": best["feature_class"],
            "feature_code":  best["feature_code"],
            "admin1":        best["admin1"],
            "admin2":        best["admin2"],
            "population":    best["population"],
            "source":        "geonames_local",
            "match_type":    match_type,
            "match_score":   round(best_score, 4),
        }

    def _fuzzy_lookup(self, norm: str) -> dict | None:
        query_trigrams = _make_trigrams(norm)
        if not query_trigrams:
            return None

        overlap: dict[str, int] = {}
        for tg in query_trigrams:
            for name_key in self._trigram_index.get(tg, ()):
                overlap[name_key] = overlap.get(name_key, 0) + 1

        if not overlap:
            return None

        top_keys = sorted(overlap, key=lambda k: overlap[k], reverse=True)[
            : self.max_fuzzy_candidates
        ]

        best_sim = 0.0
        best_candidates: list[dict] = []

        for key in top_keys:
            sim = difflib.SequenceMatcher(None, norm, key).ratio()
            if sim > best_sim:
                best_sim = sim
                best_candidates = self._index[key]
            elif sim == best_sim:
                best_candidates.extend(self._index[key])

        if best_sim < self.fuzzy_threshold:
            logger.debug(
                "Fuzzy match below threshold for %r (best=%.3f < %.3f)",
                norm, best_sim, self.fuzzy_threshold,
            )
            return None

        return self._best(best_candidates, match_type="fuzzy", query=norm)