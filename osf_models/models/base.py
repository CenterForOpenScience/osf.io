import random

import modularodm.exceptions
from django.db import models
from osf_models.models.mixins import Versioned

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


class BaseModel(models.Model):
    class Meta:
        abstract = True

    @classmethod
    def load(cls, id):
        try:
            if issubclass(cls, GuidMixin):
                return cls.objects.get(_guid__guid=id)
            return cls.objects.getQ(pk=id)
        except cls.DoesNotExist:
            return None

    @classmethod
    def find_one(cls, query):
        try:
            return cls.objects.get(query.to_django_query())
        except cls.DoesNotExist:
            raise modularodm.exceptions.NoResultsFound()
        except cls.MultipleObjectsReturned as e:
            raise modularodm.exceptions.MultipleResultsFound(*e.args)

    @classmethod
    def find(cls, query):
        return cls.objects.filter(query.to_django_query())
