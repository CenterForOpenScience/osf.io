from framework.mongo import *

import datetime

class Keyword(MongoObject):
    schema = {
        '_id':{},
        'type':{'type':lambda: dict()},
    }
    _doc = {
        'name':'keyword',
        'version':1,
    }

Keyword.setStorage(MongoCollectionStorage(db, 'keyword'))
