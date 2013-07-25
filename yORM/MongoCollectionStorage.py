import logging; logging.basicConfig(level=logging.DEBUG);
logger = logging.getLogger('MongoStorage')

import yORM

from bson.objectid import ObjectId
from bson.dbref import DBRef

class MongoCollectionStorage(yORM.Storage):
    def __init__(self, db, collection):
        self.collection = collection
        self.db = db[self.collection] # this db is a collection
    
    def open(self):
        pass
    
    def set(self, pkey, value):
        return self.db.insert(value, safe=True)
    
    def update(self, pkey, value):
        self.db.save(value)
    
    def find(self, **kwargs):
        result = self.db.find(kwargs)
        return result

    def get(self, pkey):
        #if not isinstance(pkey, ObjectId):
        #    pkey = ObjectId(str(pkey))
        return self.db.find_one({'_id':pkey})
        
    def remove(self, pkey):
        return True
    
    def get_ref(self, obj):
        return unicode(obj._id) # DBRef(self.collection, obj._id, database=self.db.database.name) #str(obj._id) #
    
    #def get_from_ref(self, parentClass, ref):
    #    return parentClass.load(ref)
    
    def get_from_ref(self, ref):
        return self.db.find_one({'_id':ref._id})
    
    def keys(self):
        pass       
    
    def close(self):
        pass