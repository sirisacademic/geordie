from geopy.geocoders import Nominatim
import time

class EntityLinker:
    def __init__(self, device):
        device=device
        self.app = Nominatim(user_agent="siris_app")

    def link_entities(self, entities_in_sentence):
        result = []
        for item in entities_in_sentence:
            entity = item['entity']
            res = self.app.geocode(entity, addressdetails=True, language ="en", extratags=True)
            item['osm'] = res.raw
            result.append(item)
            time.sleep(5)
        return result
