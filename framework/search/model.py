from framework.mongo import db

from modularodm import StoredObject
from modularodm import fields
from modularodm import storage

import datetime

class Keyword(StoredObject):
    _id = fields.StringField(primary=True)
    type = fields.DictionaryField()

    _meta = {'optimistic' : True}

Keyword.set_storage(storage.MongoStorage(db, 'keyword'))