from framework.mongo import db

from framework import StoredObject, fields, storage

import datetime

class Keyword(StoredObject):
    _id = fields.StringField(primary=True)
    type = fields.DictionaryField()

    _meta = {'optimistic' : True}
