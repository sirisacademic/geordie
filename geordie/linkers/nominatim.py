"""Nominatim (OpenStreetMap) entity linker with persistent SQLite cache."""

from __future__ import annotations

from pathlib import Path

from .base import BaseLinker, default_cache_path  # single clean import

KEYS_TO_EXTRACT = ["place_id", "lat", "lon", "name", "importance", "osm_type", "osm_id"]
ADDRESS_KEYS = [
    "municipality", "city", "town", "village", "county",
    "state", "province", "state_district", "country", "country_code",
]
EXTRATAG_KEYS = ["wikidata", "wikipedia"]


class NominatimLinker(BaseLinker):
    """
    Entity linker backed by the Nominatim geocoding API.

    Parameters
    ----------
    user_agent : str
        User-agent string for Nominatim (required by their TOS).
    language : str
        Preferred language for results (ISO 639-1).
    cache_path : str or Path or None
        Path to a SQLite file for persistent caching.
        Defaults to ``~/.cache/geordie/nominatim.db``.
    cache_maxsize : int
        Max entries in the cache before LRU eviction.
    cache_ttl : float or None
        Time-to-live in seconds for cache entries. None = no expiry.
    importance_threshold : float
        Discard Nominatim results below this importance score.
    sleep_between_calls : float
        Seconds to wait between Nominatim API calls (respect rate limits).
    addressdetails : bool
        Request address breakdown from Nominatim.
    extratags : bool
        Request extra tags (wikidata, wikipedia) from Nominatim.
    """

    def __init__(
        self,
        user_agent: str = "geordie_lib",
        language: str = "en",
        cache_path: str | Path | None = None,
        cache_maxsize: int = 50_000,
        cache_ttl: float | None = None,        # dropped Optional[] — Python 3.10+
        importance_threshold: float = 0.0,
        sleep_between_calls: float = 1.1,
        addressdetails: bool = True,
        extratags: bool = True,
    ):
        if cache_path is None:
            cache_path = default_cache_path("nominatim.db")

        super().__init__(
            cache_path=cache_path,
            cache_maxsize=cache_maxsize,
            cache_ttl=cache_ttl,
            sleep_between_calls=sleep_between_calls,
        )

        # geopy imported here — lazy, so the module loads even without geopy installed
        from geopy.geocoders import Nominatim
        self.geolocator = Nominatim(user_agent=user_agent)
        self.language = language
        self.importance_threshold = importance_threshold
        self.addressdetails = addressdetails
        self.extratags = extratags

    def _make_key(self, entity: str) -> str:
        e = (entity or "").strip().lower()
        return f"nom|{e}|lang={self.language}"

    def _lookup(self, entity: str) -> dict | None:
        # geopy imported here too — lazy for the same reason
        from geopy.exc import GeocoderServiceError, GeocoderTimedOut

        try:
            res = self.geolocator.geocode(
                entity,
                addressdetails=self.addressdetails,
                language=self.language,
                extratags=self.extratags,
            )
        except (GeocoderTimedOut, GeocoderServiceError) as exc:
            self._logger.warning("Nominatim error for %r: %s", entity, exc)
            return None

        if res is None:
            return None

        raw = res.raw
        importance = float(raw.get("importance") or 0.0)
        if importance < self.importance_threshold:
            return None

        result: dict = {k: raw.get(k) for k in KEYS_TO_EXTRACT}

        # Cast lat/lon to float — Nominatim returns them as strings
        try:
            result["lat"] = float(result["lat"])
            result["lon"] = float(result["lon"])
        except (TypeError, ValueError):
            result["lat"] = None
            result["lon"] = None

        # OSM class and type from top-level raw response
        result["osm_class"] = raw.get("class")   # e.g. "boundary", "place", "highway"
        result["osm_type"]  = raw.get("type")    # e.g. "administrative", "city", "river"

        address = raw.get("address")
        if isinstance(address, dict) and address:
            result["address_type"] = next(iter(address.keys()), None)
            for k in ADDRESS_KEYS:
                result[k] = address.get(k)
        else:
            result["address_type"] = None
            for k in ADDRESS_KEYS:
                result[k] = None

        extra = raw.get("extratags")
        if isinstance(extra, dict):
            for k in EXTRATAG_KEYS:
                result[k] = extra.get(k)
        else:
            for k in EXTRATAG_KEYS:
                result[k] = None

        result["source"] = "nominatim"   # added — was missing
        return result