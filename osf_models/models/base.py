import random

import modularodm.exceptions
from modularodm.query import QueryGroup

from django.db import models
from osf_models.modm_compat import to_django_query

ALPHABET = '23456789abcdefghjkmnpqrstuvwxyz'


def generate_guid(length=5):
    while True:
        guid_id = ''.join(random.sample(ALPHABET, length))

        try:
            # is the guid in the blacklist
            BlackListGuid.objects.get(guid=guid_id)
        except BlackListGuid.DoesNotExist:
            # it's not, check and see if it's already in the database
            try:
                Guid.objects.get(guid=guid_id)
            except Guid.DoesNotExist:
                # valid and unique guid
                return guid_id


class Guid(models.Model):
    id = models.AutoField(primary_key=True)
    guid = models.fields.CharField(max_length=255,
                                   default=generate_guid,
                                   unique=True,
                                   db_index=True)


class BlackListGuid(models.Model):
    id = models.AutoField(primary_key=True)
    guid = models.fields.CharField(max_length=255, unique=True, db_index=True)


def generate_guid_instance():
    return Guid.objects.create().id


class PKIDStr(str):
    def __new__(self, _id, pk):
        return str.__new__(self, _id)

    def __init__(self, _id, pk):
        self.__pk = pk

    def __int__(self):
        return self.__pk


class GuidMixin(models.Model):
    _guid = models.OneToOneField(Guid,
                                 default=generate_guid_instance,
                                 unique=True,
                                 related_name='referent_%(class)s')

    @property
    def guid(self):
        return self._guid.guid

    @property
    def _id(self):
        return PKIDStr(self._guid.guid, self.pk)

    class Meta:
        abstract = True

class MODMCompatibilityQuerySet(models.QuerySet):
    def sort(self, *fields):
        # Fields are passed in as e.g. [('title', 1), ('date_created', -1)]
        if isinstance(fields[0], list):
            fields = fields[0]
        def sort_key(item):
            if isinstance(item, basestring):
                return item
            elif isinstance(item, tuple):
                field_name, direction = item
                prefix = '-' if direction == -1 else ''
                return ''.join([prefix, field_name])
        sort_keys = [sort_key(each) for each in fields]
        return self.order_by(*sort_keys)

    def limit(self, n):
        return self[:n]

class BaseModel(models.Model):
    """Base model that acts makes subclasses mostly compatible with the
    modular-odm ``StoredObject`` interface.
    ."""

    objects = MODMCompatibilityQuerySet.as_manager()

    class Meta:
        abstract = True

    @classmethod
    def load(cls, data):
        try:
            if issubclass(cls, GuidMixin):
                return cls.objects.get(_guid__guid=data)
            return cls.objects.getQ(pk=data)
        except cls.DoesNotExist:
            return None

    @classmethod
    def find_one(cls, query):
        try:
            return cls.objects.get(to_django_query(query, model_cls=cls))
        except cls.DoesNotExist:
            raise modularodm.exceptions.NoResultsFound()
        except cls.MultipleObjectsReturned as e:
            raise modularodm.exceptions.MultipleResultsFound(*e.args)

    @classmethod
    def find(cls, query=None):
        if not query:
            return cls.objects.all()
        else:
            return cls.objects.filter(to_django_query(query, model_cls=cls))

    @property
    def _primary_name(self):
        return '_id'
