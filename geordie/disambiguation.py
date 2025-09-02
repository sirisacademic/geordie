from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
import time
import os
import copy
import logging
from typing import Optional
from collections import OrderedDict
import pandas as pd

# from .utils import cache_new_results

keys_to_extract = ['place_id', 'lat', 'lon', 'name']
address_keys_to_extract = ["municipality", "city", "town", "village", "county", "state", "province", "state_district", "country"]
extratags_keys_to_extract = ["wikidata", "wikipedia"] 

script_dir = os.path.dirname(os.path.abspath(__file__))

class EntityLinker:
    """
    Entity linker with in-memory LRU cache for Nominatim geocoding.
    - Caches both positive and negative results (None) per entity string and query params.
    - Optional TTL so entries expire after some seconds (set cache_ttl=None to disable).
    - LRU eviction when cache exceeds cache_maxsize.
    """
    def __init__(
        self,
        device=None,
        user_agent: str = "siris_app",
        cache_maxsize: int = 5000,
        cache_ttl: Optional[float] = None,   # e.g. 86400 for 1 day
        importance_threshold: float = 0.0,
        language: str = "en",
        addressdetails: bool = True,
        extratags: bool = True,
        sleep_between_calls: float = 0.0
    ):
        self.device = device
        self.app = Nominatim(user_agent=user_agent)
        self.cache_maxsize = cache_maxsize
        self.cache_ttl = cache_ttl
        self.importance_threshold = importance_threshold
        self.language = language
        self.addressdetails = addressdetails
        self.extratags = extratags
        # simple LRU via OrderedDict: {key: (timestamp, value)}
        self._cache: OrderedDict[str, tuple[float, dict | None]] = OrderedDict()
        self._logger = logging.getLogger(__name__)
        self._sleep = sleep_between_calls

    # ---------------- Cache helpers ----------------
    def _make_key(self, entity: str) -> str:
        # Normalize entity text and incorporate params that can change results
        e = (entity or "").strip().lower()
        return f"{e}||lang={self.language}|addr={int(self.addressdetails)}|extra={int(self.extratags)}"

    def _cache_get(self, key: str):
        if key not in self._cache:
            return None
        ts, value = self._cache[key]
        # TTL check
        if self.cache_ttl is not None and (time.time() - ts) > self.cache_ttl:
            # expired
            try:
                del self._cache[key]
            except KeyError:
                pass
            return None
        # refresh LRU order
        self._cache.move_to_end(key, last=True)
        # return a deep copy to avoid callers mutating cached structures
        return copy.deepcopy(value)

    def _cache_set(self, key: str, value):
        # evict if needed
        while len(self._cache) >= self.cache_maxsize:
            self._cache.popitem(last=False)  # pop oldest (LRU)
        self._cache[key] = (time.time(), copy.deepcopy(value))
        self._cache.move_to_end(key, last=True)

    def clear_cache(self):
        self._cache.clear()

    # ---------------- Main API ----------------
    def link_entities(self, entities_in_sentence):
        result = []

        for item in entities_in_sentence:
            entity = item.get('entity_normalised') or item.get('entity') or ""
            key = self._make_key(entity)

            cached = self._cache_get(key)
            if cached is not None:
                # cached is a dict like {"osm": {...} or None, "osm_raw": {...} or None}
                item.update(cached)
                result.append(item)
                continue

            # Not in cache → call Nominatim
            try:
                res = self.app.geocode(
                    entity,
                    addressdetails=self.addressdetails,
                    language=self.language,
                    extratags=self.extratags,
                )
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                self._logger.warning(f"Nominatim error for '{entity}': {e}")
                item["osm"] = None
                item["osm_raw"] = None
                # Cache the negative result to avoid hammering on repeated failures
                self._cache_set(key, {"osm": None, "osm_raw": None})
                result.append(item)
                continue

            # No result found
            if res is None:
                item["osm"] = None
                item["osm_raw"] = None
                self._cache_set(key, {"osm": None, "osm_raw": None})
                result.append(item)
                if self._sleep:
                    time.sleep(self._sleep)
                continue

            result_osm = res.raw

            # Filter by importance to avoid low-confidence matches
            importance = result_osm.get("importance", 0.0) or 0.0
            if importance < self.importance_threshold:
                item["osm"] = None
                item["osm_raw"] = None
                self._cache_set(key, {"osm": None, "osm_raw": None})
                result.append(item)
                if self._sleep:
                    time.sleep(self._sleep)
                continue

            # Build compact subset
            subset = {k: result_osm.get(k) for k in keys_to_extract}

            address = result_osm.get("address")
            if address is not None and isinstance(address, dict) and address:
                # a rough "entity_type" as the first key in address (kept from your logic)
                subset["entity_type"] = list(address.keys())[0]
                address_subset = {k: address.get(k) for k in address_keys_to_extract}
            else:
                address_subset = {k: None for k in address_keys_to_extract}
            subset.update(address_subset)

            extratags = result_osm.get("extratags")
            if extratags is not None and isinstance(extratags, dict):
                extratags_subset = {k: extratags.get(k) for k in extratags_keys_to_extract}
            else:
                extratags_subset = {k: None for k in extratags_keys_to_extract}
            subset.update(extratags_subset)

            item['osm'] = subset
            item['osm_raw'] = result_osm

            # Store in cache
            self._cache_set(key, {"osm": subset, "osm_raw": result_osm})

            result.append(item)

            if self._sleep:
                time.sleep(self._sleep)

        return result
