from framework.mongo import MongoCollectionStorage, MongoObject, db

from modularodm import StoredObject
from modularodm import fields
from modularodm import storage

import datetime

# class Keyword(MongoObject):
class Keyword(StoredObject):
    # schema = {
    #     '_id':{},
    #     'type':{'type':lambda: dict()},
    # }
    # _doc = {
    #     'name':'keyword',
    #     'version':1,
    # }

    _id = fields.StringField(primary=True)
    type = fields.DictionaryField()

# Keyword.setStorage(MongoCollectionStorage(db, 'keyword'))
Keyword.set_storage(storage.MongoStorage(db, 'keyword'))