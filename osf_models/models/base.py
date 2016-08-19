import logging
import random
from datetime import datetime

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
import modularodm.exceptions
import pytz

from osf_models.exceptions import ValidationError
from osf_models.modm_compat import to_django_query
from osf_models.utils.base import get_object_id

ALPHABET = '23456789abcdefghjkmnpqrstuvwxyz'

logger = logging.getLogger(__name__)

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
            elif issubclass(cls, ObjectIDMixin):
                return cls.objects.get(guid=data)
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

    @classmethod
    def remove(cls, query):
        return cls.find(query).delete()

    @classmethod
    def remove_one(cls, obj):
        if obj.pk:
            return obj.delete()

    @property
    def _primary_name(self):
        return '_id'

    def clone(self):
        """Create a new, unsaved copy of this object."""
        copy = self.__class__.objects.get(pk=self.pk)
        copy.id = None
        return copy

    def save(self, *args, **kwargs):
        # Make Django validate on save (like modm)
        if not kwargs.get('force_insert') and not kwargs.get('force_update'):
            try:
                self.full_clean()
            except DjangoValidationError as err:
                raise ValidationError(*err.args)
        return super(BaseModel, self).save(*args, **kwargs)

    @classmethod
    def migrate_from_modm(cls, modm_obj):
        """
        Given a modm object, make a django object with the same local fields.

        This is a base method that may work for simple objects. It should be customized in the child class if it
        doesn't work.
        :param modm_obj:
        :return:
        """
        django_obj = cls()

        local_django_fields = set([x.name for x in django_obj._meta.get_fields() if not x.is_relation])

        intersecting_fields = set(modm_obj.to_storage().keys()).intersection(
            set(local_django_fields))

        for field in intersecting_fields:
            modm_value = getattr(modm_obj, field)
            if modm_value is None:
                continue
            if isinstance(modm_value, datetime):
                modm_value = pytz.utc.localize(modm_value)
            setattr(django_obj, field, modm_value)

        return django_obj


class Guid(BaseModel):
    id = models.AutoField(primary_key=True)
    guid = models.fields.CharField(max_length=255,
                                   default=generate_guid,
                                   unique=True,
                                   db_index=True)

    # Override load in order to load by GUID
    @classmethod
    def load(cls, data):
        try:
            return cls.objects.get(guid=data)
        except cls.DoesNotExist:
            return None

    @property
    def referent(self):
        """The model instance that this Guid refers to. May return an instance of
        any model that inherits from GuidMixin.
        """
        # Because the related_name for '_guid' is dynamic (e.g. 'referent_osfuser'), we need to check each one-to-one field
        # until we find a match
        referent_fields = (each for each in self._meta.get_fields() if each.one_to_one and each.name.startswith('referent'))
        for relationship in referent_fields:
            try:
                return getattr(self, relationship.name)
            except relationship.related_model.DoesNotExist:
                continue
        return None

    @referent.setter
    def referent(self, obj):
        obj._guid = self


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


class MODMCompatibilityGuidQuerySet(MODMCompatibilityQuerySet):

    def get_by_guid(self, guid):
        return self.get(_guid__guid=guid)


class BaseIDMixin(models.Model):

    @classmethod
    def load(cls, q):
        raise NotImplementedError('You must define a load method.')

    @classmethod
    def migrate_from_modm(cls, modm_obj):
        """
        Given a modm object, make a django object with the same local fields.

        This is a base method that may work for simple objects. It should be customized in the child class if it
        doesn't work.
        :param modm_obj:
        :return:
        """
        raise NotImplementedError('You must define a migrate_from_modm method.')

    class Meta:
        abstract = True


class ObjectIDMixin(BaseIDMixin):
    guid = models.CharField(max_length=255,
                                  unique=True,
                                  db_index=True,
                                  default=get_object_id)

    @property
    def _object_id(self):
        return self.guid

    @property
    def _id(self):
        return PKIDStr(self._object_id, self.pk)

    @classmethod
    def load(cls, q):
        # modm doesn't throw exceptions when loading things that don't exist
        try:
            return cls.objects.get(guid=q)
        except cls.DoesNotExist:
            return None

    _primary_key = _id

    def clone(self):
        ret = super(ObjectIDMixin, self).clone()
        ret.guid = None
        return ret

    def save(self, *args, **kwargs):
        if not self.guid:
            self.guid = get_object_id()
        return super(ObjectIDMixin, self).save(*args, **kwargs)

    @classmethod
    def migrate_from_modm(cls, modm_obj):
        """
        Given a modm object, make a django object with the same local fields.

        This is a base method that may work for simple objects. It should be customized
        in the child class if it doesn't work.
        :param modm_obj:
        :return:
        """
        django_obj = cls()

        local_django_fields = set([x.name for x in django_obj._meta.get_fields() if not x.is_relation])

        intersecting_fields = set(modm_obj.to_storage().keys()).intersection(
            set(local_django_fields))

        for field in intersecting_fields:
            modm_value = getattr(modm_obj, field)
            if modm_value is None:
                continue
            if isinstance(modm_value, datetime):
                modm_value = pytz.utc.localize(modm_value)
            setattr(django_obj, field, modm_value)

        return django_obj

    class Meta:
        abstract = True


class GuidMixin(BaseIDMixin):
    _guid = models.OneToOneField('Guid',
                                 default=generate_guid_instance,
                                 null=True, blank=True,
                                 unique=True,
                                 related_name='referent_%(class)s')

    objects = MODMCompatibilityGuidQuerySet.as_manager()

    @property
    def guid(self):
        return self._guid.guid

    @property
    def _id(self):
        return PKIDStr(self._guid.guid, self.pk)

    @property
    def deep_url(self):
        return None

    @classmethod
    def load(cls, q):
        # modm doesn't throw exceptions when loading things that don't exist
        try:
            return cls.objects.get(_guid__guid=q)
        except cls.DoesNotExist:
            return None

    _primary_key = _id

    def clone(self):
        ret = super(GuidMixin, self).clone()
        ret._guid = None
        return ret

    def save(self, *args, **kwargs):
        if not self._guid:
            self._guid = Guid.objects.create()
        return super(GuidMixin, self).save(*args, **kwargs)

    @classmethod
    def migrate_from_modm(cls, modm_obj):
        """
        Given a modm object, make a django object with the same local fields.
        This is a base method that may work for simple things. It should be customized for complex ones.
        :param modm_obj:
        :return:
        """
        guid, created = Guid.objects.get_or_create(guid=modm_obj._id)
        if created:
            logger.debug('Created a new Guid for {}'.format(modm_obj))
        django_obj = cls()
        django_obj._guid = guid

        local_django_fields = set([x.name for x in django_obj._meta.get_fields() if not x.is_relation])

        intersecting_fields = set(modm_obj.to_storage().keys()).intersection(
            set(local_django_fields))

        for field in intersecting_fields:
            modm_value = getattr(modm_obj, field)
            if modm_value is None:
                continue
            if isinstance(modm_value, datetime):
                modm_value = pytz.utc.localize(modm_value)
            setattr(django_obj, field, modm_value)

        return django_obj

    class Meta:
        abstract = True
