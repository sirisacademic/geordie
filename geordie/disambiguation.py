from geopy.geocoders import Nominatim
import time

keys_to_extract = ['place_id', 'lat', 'lon', 'name']
address_keys_to_extract = ["municipality", "city", "town", "village", "county", "state", "province", "state_district", "country"]
extratags_keys_to_extract = ["wikidata", "wikipedia"] 

class EntityLinker:
    def __init__(self, device):
        device=device
        self.app = Nominatim(user_agent="siris_app")

    def link_entities(self, entities_in_sentence):
        result = []
        for item in entities_in_sentence:
            entity = item['entity_normalised']
            try:
                res = self.app.geocode(entity, addressdetails=True, language ="en", extratags=True)

                # Extracting subset of keys with fallback for missing keys
                subset = {key: res.raw.get(key, None) for key in keys_to_extract}

                if res["raw"].get("address", None) is not None:
                    address = res["raw"].get("address", None)
                    subset["entity_type"] = list(address.keys())[0]
                    # Extracting subset of keys with fallback for missing keys
                    address_subset = {key: address.get(key, None) for key in address_keys_to_extract}
                else:
                    # Adding null results for non-existing keys, so all results have the same structure.
                    address_subset = {key: None for key in address_keys_to_extract}
                subset.update(address_subset)

                if res["raw"].get("extratags", None) is not None:
                    extratags = res["raw"].get("extratags", None)
                    # Extracting subset of keys with fallback for missing keys
                    extratags_subset = {key: extratags.get(key, None) for key in extratags_keys_to_extract}
                else:
                    # Adding null results for non-existing keys, so all results have the same structure.
                    extratags_subset = {key: None for key in extratags_keys_to_extract}
                subset.update(extratags_subset)

                item['osm'] = subset
            except:
                item['osm'] = None
            result.append(item)
            time.sleep(5)
        return result
