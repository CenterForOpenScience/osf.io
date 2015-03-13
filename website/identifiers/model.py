# -*- coding: utf-8 -*-

from bson import ObjectId

from modularodm import Q
from modularodm import fields
from modularodm.storage.base import KeyExistsException

from framework.mongo import StoredObject
from framework.mongo.utils import unique_on


@unique_on(['referent.0', 'referent.1', 'category'])
class Identifier(StoredObject):
    _id = fields.StringField(default=lambda: str(ObjectId()))
    referent = fields.AbstractForeignField()
    category = fields.StringField()
    value = fields.StringField()


class IdentifierMixin(object):

    def get_identifier(self, category):
        identifiers = Identifier.find(
            Q('referent', 'eq', self) &
            Q('category', 'eq', category)
        )
        return identifiers[0] if identifiers else None

    def get_identifier_value(self, category):
        identifier = self.get_identifier(category)
        return identifier.value if identifier else None

    def set_identifier(self, category, value):
        try:
            identifier = Identifier(referent=self, category=category, value=value)
            identifier.save()
        except KeyExistsException:
            identifier = self.get_identifier(category)
            assert identifier is not None
            identifier.category = category
            identifier.save()
