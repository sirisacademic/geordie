from geopy.geocoders import Nominatim
import time
import os
import pandas as pd
from .utils import cache_new_results

keys_to_extract = ['place_id', 'lat', 'lon', 'name']
address_keys_to_extract = ["municipality", "city", "town", "village", "county", "state", "province", "state_district", "country"]
extratags_keys_to_extract = ["wikidata", "wikipedia"] 

script_dir = os.path.dirname(os.path.abspath(__file__))
relative_path_static_cache = os.path.join(script_dir, 'data', 'static_cache.pkl')
relative_path_tmp_cache = os.path.join(script_dir, 'data', 'tmp_cache.pkl')

class EntityLinker:
    def __init__(self, device):
        device=device
        self.app = Nominatim(user_agent="siris_app")

    def link_entities(self, entities_in_sentence):
        result = []
        new_results = {}
        static_cache = pd.read_pickle(relative_path_static_cache)
        if os.path.isfile(relative_path_tmp_cache):
            tmp_cache = pd.read_pickle(relative_path_tmp_cache)
        else:
            tmp_cache= {}

        for item in entities_in_sentence:
            entity = item['entity_normalised']
            try:
                # Checking if entity is in static_cache.
                if entity in static_cache.keys():
                    result_osm = static_cache[entity]

                # Checking if entity is in tmp_cache.
                elif entity in tmp_cache.keys():
                    result_osm = tmp_cache[entity]

                # If not found in either cache, calling OSM.
                else:
                    res = self.app.geocode(entity, addressdetails=True, language ="en", extratags=True)
                    new_results[entity] = res.raw
                    result_osm = res.raw
                
                # Filter out results that do not surpass a certain threshold probability to avoid false positives.
                if result_osm["importance"]>=0.6: # Change importance threshold as needed.
                    
                    # Extracting subset of keys with fallback for missing keys
                    subset = {key: result_osm.get(key, None) for key in keys_to_extract}

                    if result_osm.get("address", None) is not None:
                        address = result_osm.get("address", None)
                        subset["entity_type"] = list(address.keys())[0]
                        # Extracting subset of keys with fallback for missing keys
                        address_subset = {key: address.get(key, None) for key in address_keys_to_extract}
                    else:
                        # Adding null results for non-existing keys, so all results have the same structure.
                        address_subset = {key: None for key in address_keys_to_extract}
                    subset.update(address_subset)

                    if result_osm.get("extratags", None) is not None:
                        extratags = result_osm.get("extratags", None)
                        # Extracting subset of keys with fallback for missing keys
                        extratags_subset = {key: extratags.get(key, None) for key in extratags_keys_to_extract}
                    else:
                        # Adding null results for non-existing keys, so all results have the same structure.
                        extratags_subset = {key: None for key in extratags_keys_to_extract}
                    subset.update(extratags_subset)

                    item['osm'] = subset
                else:
                    item["osm"] = None
            except:
                item['osm'] = None
            result.append(item)
            time.sleep(5)

        cache_new_results(new_results)
        return result



