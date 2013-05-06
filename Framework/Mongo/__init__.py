###############################################################################

from pymongo import Connection
from bson.objectid import ObjectId
from bson.dbref import DBRef

import random

from yORM import *

import Site.Settings

ObjectId = ObjectId
DBRef = DBRef
connect = Connection('localhost', 20771)
# admin / osf
# adminpassword / osfosfosfosf0$f
db = connect[Site.Settings.database]
db.authenticate('osf', 'osfosfosfosf0$f')

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