from geopy.geocoders import Nominatim
import pandas as pd
import time

keys_to_extract = ['place_id', 'lat', 'lon', 'name', 'address','extratags']

class EntityLinker:
    def __init__(self, device):
        device=device
        self.app = Nominatim(user_agent="siris_app")

    def link_entities(self, entities_in_sentence):
        result = []
        for item in entities_in_sentence:
            entity = item['entity']
            try:
                res = self.app.geocode(entity, addressdetails=True, language ="en", extratags=True)

                # Extracting subset of keys with fallback for missing keys
                subset = {key: res.raw.get(key, None) for key in keys_to_extract}

                item['osm'] = subset
            except:
                item['osm'] = None
            result.append(item)
            time.sleep(5)
        return result
