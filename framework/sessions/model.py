# -*- coding: utf-8 -*-

from bson import ObjectId
from modularodm import fields

from framework.mongo import StoredObject


class Session(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    date_created = fields.DateTimeField(auto_now_add=True)
    date_modified = fields.DateTimeField(auto_now=True)
    data = fields.DictionaryField()

    def __init__(self, *args, **kwargs):
        super(Session, self).__init__(*args, **kwargs)
        # Initialize history to empty list if not found
        if 'history' not in self.data:
            self.data['history'] = []
