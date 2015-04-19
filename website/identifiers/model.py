# -*- coding: utf-8 -*-

from bson import ObjectId

from modularodm import Q
from modularodm import fields
from modularodm.storage.base import KeyExistsException

from framework.mongo import StoredObject
from framework.mongo.utils import unique_on


@unique_on(['referent.0', 'referent.1', 'category'])
class Identifier(StoredObject):
    """A persistent identifier model for DOIs, ARKs, and the like."""
    _id = fields.StringField(default=lambda: str(ObjectId()))
    # object to which the identifier points
    referent = fields.AbstractForeignField(required=True)
    # category: e.g. 'ark', 'doi'
    category = fields.StringField(required=True)
    # value: e.g. 'FK424601'
    value = fields.StringField(required=True)


class IdentifierMixin(object):
    """Model mixin that adds methods for getting and setting Identifier objects
    for model objects.
    """

    def get_identifier(self, category):
        identifiers = Identifier.find(
            Q('referent', 'eq', self) &
            Q('category', 'eq', category)
        )
        return identifiers[0] if identifiers else None

    def get_identifier_value(self, category):
        identifier = self.get_identifier(category)
        return identifier.value if identifier else None

    def set_identifier_value(self, category, value):
        try:
            identifier = Identifier(referent=self, category=category, value=value)
            identifier.save()
        except KeyExistsException:
            identifier = self.get_identifier(category)
            assert identifier is not None
            identifier.value = value
            identifier.save()
