###############################################################################

from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.dbref import DBRef

import random
import string

from yORM import Object, MongoCollectionStorage

from website import settings
from urlparse import urlsplit

client = MongoClient(settings.mongo_uri)

db_name = urlsplit(settings.mongo_uri).path[1:] # Slices off the leading slash of the path (database name)

db = client[db_name]

class MongoObject(Object):
    @property
    def id(self):
        return self._id
    
    @classmethod
    def find(self, **kwargs):

        result = super(MongoObject, self).find(**kwargs)

        if result.count() == 1:
            result = result[0]
            return self(**result)
        elif result.count() > 0:
            return result
        else:
            return None

    def generate_random_id(self):
        chars = string.letters + string.digits[2:]
        return ''.join(random.sample(chars, 5))

    def optimistic_insert(self):
        while True:
            try:
                self._id = self.generate_random_id()
                self.insert()
            except:
                continue
            break