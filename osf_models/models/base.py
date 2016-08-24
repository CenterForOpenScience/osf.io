import logging
import random
from datetime import datetime

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
import modularodm.exceptions
import pytz

from osf_models.exceptions import ValidationError
from osf_models.modm_compat import to_django_query, Q
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
    """

    objects = MODMCompatibilityQuerySet.as_manager()

    class Meta:
        abstract = True

    @classmethod
    def load(cls, data):
        try:
            if issubclass(cls, GuidMixin):
                return cls.objects.get(guid__guid=data)
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

    def _natural_key(self):
        return self.pk

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

        This is a base method that may work for simple objects.
        It should be customized in the child class if it doesn't work.

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


# TODO: Rename to Identifier?
class Guid(BaseModel):
    id = models.AutoField(primary_key=True)
    guid = models.fields.CharField(max_length=255,
                                   unique=True,
                                   null=True,
                                   blank=True,
                                   db_index=True)

    object_id = models.CharField(max_length=255,
                                 unique=True,
                                 db_index=True,
                                 null=True,
                                 blank=True)

    def initialize_guid(self):
        self.guid = generate_guid()

    def initialize_object_id(self):
        self.object_id = get_object_id()

    # Override load in order to load by GUID
    @classmethod
    def load(cls, data):
        try:
            return cls.objects.get(guid=data)
        except cls.DoesNotExist:
            return None

    @classmethod
    def find(cls, query, *args, **kwargs):
        # Make referent queryable
        # NOTE: This won't work with compound queries
        if hasattr(query, 'attribute') and query.attribute == 'referent':
            # We rely on the fact that the related_name for BaseIDMixin.guid
            # is 'referent_<lowercased class name>'
            class_name = query.argument.__class__.__name__.lower()
            return super(Guid, cls).find(Q('referent_{}'.format(class_name), query.op, query.argument))
        else:
            return super(Guid, cls).find(query, *args, **kwargs)

    @property
    def referent(self):
        """The model instance that this Guid refers to. May return an instance of
        any model that inherits from GuidMixin.
        """
        # Because the related_name for '_guid' is dynamic (e.g. 'referent_osfuser'),
        # we need to check each one-to-one field
        # until we find a match
        referent_fields = (each for each in self._meta.get_fields()
                           if each.one_to_one and each.name.startswith('referent'))
        for relationship in referent_fields:
            try:
                return getattr(self, relationship.name)
            except relationship.related_model.DoesNotExist:
                continue
        return None

    @referent.setter
    def referent(self, obj):
        obj.guid = self


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


class BaseIDMixin(models.Model):
    guid = models.OneToOneField('Guid',
                                 default=generate_guid_instance,
                                 null=True, blank=True,
                                 unique=True,
                                 related_name='referent_%(class)s')

    @property
    def _id(self):
        if self.guid:
            identifier = getattr(self.guid, self.primary_identifier_name)
            if identifier:
                return PKIDStr(identifier, self.pk)
        return None

    _primary_key = _id

    @classmethod
    def load(cls, q):
        # modm doesn't throw exceptions when loading things that don't exist
        kwargs = {'guid__{}'.format(cls.primary_identifier_name): q}
        try:
            return cls.objects.get(**kwargs)
        except cls.DoesNotExist:
            return None

    def clone(self):
        ret = super(BaseIDMixin, self).clone()
        ret.guid = None
        return ret

    def save(self, *args, **kwargs):
        if not self.guid:
            self.guid = Guid.objects.create()
        if not getattr(self.guid, self.primary_identifier_name, None):
            # TODO: Reduce magic?
            initialization_method = getattr(self.guid, 'initialize_' + self.primary_identifier_name)
            initialization_method()
            self.guid.save()
        return super(BaseIDMixin, self).save(*args, **kwargs)

    @classmethod
    def migrate_from_modm(cls, modm_obj):
        """
        Given a modm object, make a django object with the same local fields.
        This is a base method that may work for simple things. It should be customized for complex ones.

        :param modm_obj:
        :return:
        """
        kwargs = {cls.primary_identifier_name: modm_obj._id}
        guid, created = Guid.objects.get_or_create(**kwargs)
        if created:
            logger.debug('Created a new Guid for {}'.format(modm_obj))
        django_obj = cls()
        django_obj.guid = guid

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


class ObjectIDMixin(BaseIDMixin):
    primary_identifier_name = 'object_id'

    class Meta:
        abstract = True

# TODO: Implement a manager that does select_related('guid')
class MODMCompatibilityGuidQuerySet(MODMCompatibilityQuerySet):

    def get_by_guid(self, guid):
        return self.get(guid__guid=guid)


class GuidMixin(BaseIDMixin):
    objects = MODMCompatibilityGuidQuerySet.as_manager()

    primary_identifier_name = 'guid'

    @property
    def deep_url(self):
        return None

    class Meta:
        abstract = True
