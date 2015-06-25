# -*- coding: utf-8 -*-

from bson import ObjectId
from modularodm import fields

from framework.mongo import StoredObject


class Session(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    date_created = fields.DateTimeField(auto_now_add=True)
    date_modified = fields.DateTimeField(auto_now=True)
    data = fields.DictionaryField()
