import random

from django.db import models

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
    guid = models.fields.CharField(max_length=255, default=generate_guid, unique=True, db_index=True)


class BlackListGuid(models.Model):
    id = models.AutoField(primary_key=True)
    guid = models.fields.CharField(max_length=255, unique=True, db_index=True)


def generate_guid_instance():
    return Guid.objects.create().id


class BaseModel(models.Model):
    id = models.AutoField(primary_key=True)
    _guid = models.OneToOneField(Guid, default=generate_guid_instance, unique=True, related_name='referent_%(class)s')

    @property
    def guid(self):
        return self._guid.guid

    @property
    def _id(self):
        return self._guid.guid

    class Meta:
        abstract = True
