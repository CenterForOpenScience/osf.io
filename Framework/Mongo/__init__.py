###############################################################################

from pymongo import Connection
from bson.objectid import ObjectId
from bson.dbref import DBRef

import random

from yORM import *

import Site.Settings
from urlparse import urlsplit

ObjectId = ObjectId
DBRef = DBRef
connect = Connection(Site.Settings.mongo_uri)

collection = urlsplit(Site.Settings.mongo_uri).path[1:] # Slices off the leading slash of the path (collection name)

db = connect[collection]

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
        NUMBERS = '23456789'
        LOWERS = 'abcdefghijkmnpqrstuvwxyz'
        UPPERS = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
        return ''.join(random.sample(NUMBERS+LOWERS+UPPERS, 5))

    def optimistic_insert(self):
        while True:
            try:
                self._id = self.generate_random_id()
                self.insert()
            except:
                continue
            break