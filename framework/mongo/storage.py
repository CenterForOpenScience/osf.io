# -*- coding: utf-8 -*-
from modularodm.storage.mongostorage import (
    MongoQuerySet as DefaultMongoQuerySet,
    MongoStorage as DefaultMongoStorage,
)

class MongoQuerySet(DefaultMongoQuerySet):

    def __iter__(self, raw=False):
        cursor = self.data.clone() if hasattr(self.data, 'clone') else self.data
        if raw:
            return [each[self.primary] for each in cursor]
        return (self.schema.load(data=each) for each in cursor)

class MongoStorage(DefaultMongoStorage):
    QuerySet = MongoQuerySet
