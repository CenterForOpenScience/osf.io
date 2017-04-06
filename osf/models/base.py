import logging
import random

import bson
import modularodm.exceptions
from django.contrib.contenttypes.fields import (GenericForeignKey,
                                                GenericRelation)
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.db.models import ForeignKey
from django.db.models.signals import post_save
from django.dispatch import receiver
from osf.utils.caching import cached_property
from osf.exceptions import ValidationError
from osf.modm_compat import to_django_query
from osf.utils.fields import LowercaseCharField, NonNaiveDateTimeField
from osf.utils.manager import IncludeQuerySet

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
                Guid.objects.get(_id=guid_id)
            except Guid.DoesNotExist:
                # valid and unique guid
                return guid_id


def generate_object_id():
    return str(bson.ObjectId())


class MODMCompatibilityQuerySet(IncludeQuerySet):

    def eager(self, *fields):
        qs = self._clone()
        field_set = set(fields)
        fk_fields = set(qs.model.get_fk_field_names()) & field_set
        m2m_fields = set(qs.model.get_m2m_field_names()) & field_set
        if 'contributors' in field_set:
            m2m_fields.add('_contributors')
        qs = qs.select_related(*fk_fields).prefetch_related(*m2m_fields)
        return qs

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

    migration_page_size = 50000

    objects = MODMCompatibilityQuerySet.as_manager()

    class Meta:
        abstract = True

    def __unicode__(self):
        return '{}'.format(self.id)

    def to_storage(self):
        local_django_fields = set([x.name for x in self._meta.concrete_fields])
        return {name: self.serializable_value(name) for name in local_django_fields}

    @classmethod
    def get_fk_field_names(cls):
        return [field.name for field in cls._meta.get_fields() if
                    field.is_relation and not field.auto_created and (field.many_to_one or field.one_to_one) and not isinstance(field, GenericForeignKey)]

    @classmethod
    def get_m2m_field_names(cls):
        return [field.attname or field.name for field in
                     cls._meta.get_fields() if
                     field.is_relation and field.many_to_many and not hasattr(field, 'field')]

    @classmethod
    def load(cls, data):
        try:
            if isinstance(data, basestring):
                # Some models (CitationStyle) have an _id that is not a bson
                # Looking up things by pk will never work with a basestring
                return cls.objects.get(_id=data)
            return cls.objects.get(pk=data)
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
    def remove(cls, query=None):
        return cls.find(query).delete()

    @classmethod
    def remove_one(cls, obj):
        if obj.pk:
            return obj.delete()

    @property
    def _primary_name(self):
        return '_id'

    @property
    def _is_loaded(self):
        return bool(self.pk)

    def reload(self):
        return self.refresh_from_db()

    def refresh_from_db(self):
        super(BaseModel, self).refresh_from_db()
        # Django's refresh_from_db does not uncache GFKs
        for field in self._meta.virtual_fields:
            if hasattr(field, 'cache_attr') and field.cache_attr in self.__dict__:
                del self.__dict__[field.cache_attr]

    def _natural_key(self):
        return self.pk

    def clone(self):
        """Create a new, unsaved copy of this object."""
        copy = self.__class__.objects.get(pk=self.pk)
        copy.id = None

        # empty all the fks
        fk_field_names = [f.name for f in self._meta.model._meta.get_fields() if isinstance(f, (ForeignKey, GenericForeignKey))]
        for field_name in fk_field_names:
            setattr(copy, field_name, None)

        try:
            copy._id = bson.ObjectId()
        except AttributeError:
            pass
        return copy

    def save(self, *args, **kwargs):
        # Make Django validate on save (like modm)
        if not kwargs.get('force_insert') and not kwargs.get('force_update'):
            try:
                self.full_clean()
            except DjangoValidationError as err:
                raise ValidationError(*err.args)
        return super(BaseModel, self).save(*args, **kwargs)


# TODO: Rename to Identifier?
class Guid(BaseModel):
    """Stores either a short guid or long object_id for any model that inherits from BaseIDMixin.
    Each ID field (e.g. 'guid', 'object_id') MUST have an accompanying method, named with
    'initialize_<ID type>' (e.g. 'initialize_guid') that generates and sets the field.
    """
    primary_identifier_name = '_id'

    id = models.AutoField(primary_key=True)
    _id = LowercaseCharField(max_length=255, null=False, blank=False, default=generate_guid, db_index=True,
                           unique=True)
    referent = GenericForeignKey()
    content_type = models.ForeignKey(ContentType, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    created = NonNaiveDateTimeField(db_index=True, auto_now_add=True)

    def __repr__(self):
        return '<id:{0}, referent:({1})>'.format(self._id, self.referent.__repr__())

    # Override load in order to load by GUID
    @classmethod
    def load(cls, data):
        try:
            return cls.objects.get(_id=data)
        except cls.DoesNotExist:
            return None

    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'
        index_together = (
            ('content_type', 'object_id', 'created'),
        )


class BlackListGuid(BaseModel):
    id = models.AutoField(primary_key=True)
    guid = LowercaseCharField(max_length=255, unique=True, db_index=True)

    @property
    def _id(self):
        return self.guid

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
    class Meta:
        abstract = True


class ObjectIDMixin(BaseIDMixin):
    primary_identifier_name = '_id'

    _id = models.CharField(max_length=24, default=generate_object_id, unique=True, db_index=True)

    def __unicode__(self):
        return '_id: {}'.format(self._id)

    @classmethod
    def load(cls, q):
        try:
            return cls.objects.get(_id=q)
        except cls.DoesNotExist:
            # modm doesn't throw exceptions when loading things that don't exist
            return None

    class Meta:
        abstract = True

    def _natural_key(self):
        return self._id


class InvalidGuid(Exception):
    pass


class OptionalGuidMixin(BaseIDMixin):
    """
    This makes it so that things can **optionally** have guids. Think files.
    Things that inherit from this must also inherit from ObjectIDMixin ... probably
    """
    __guid_min_length__ = 5

    guids = GenericRelation(Guid, related_name='referent', related_query_name='referents')
    guid_string = ArrayField(models.CharField(max_length=255, null=True, blank=True), null=True, blank=True)
    content_type_pk = models.PositiveIntegerField(null=True, blank=True)

    def __unicode__(self):
        return '{}'.format(self.get_guid() or self.id)

    def get_guid(self, create=False):
        if not self.pk:
            logger.warn('Implicitly saving object before creating guid')
            self.save()
        if create:
            try:
                guid, created = Guid.objects.get_or_create(
                    object_id=self.pk,
                    content_type_id=ContentType.objects.get_for_model(self).pk
                )
            except MultipleObjectsReturned:
                # lol, hacks
                pass
            else:
                return guid
        return self.guids.order_by('-created').first()

    class Meta:
        abstract = True


class GuidMixinManager(type(MODMCompatibilityQuerySet.as_manager())):
    _queryset_class = IncludeQuerySet
    def get_queryset(self, *args, **kwargs):
        return super(GuidMixinManager, self).get_queryset(*args, **kwargs).include('guids')


class GuidMixin(BaseIDMixin):
    __guid_min_length__ = 5

    primary_identifier_name = 'guid_string'

    guids = GenericRelation(Guid, related_name='referent', related_query_name='referents')
    guid_string = ArrayField(models.CharField(max_length=255, null=True, blank=True), null=True, blank=True)
    content_type_pk = models.PositiveIntegerField(null=True, blank=True)

    objects = GuidMixinManager()
    # TODO: use pre-delete signal to disable delete cascade

    def __unicode__(self):
        return '{}'.format(self._id)

    def _natural_key(self):
        return self.guid_string

    @cached_property
    def _id(self):
        try:
            guid = self.guids.all()[0]
        except IndexError:
            return None
        if guid:
            return guid._id
        return None

    @_id.setter
    def _id(self, value):
        # TODO do we really want to allow this?
        guid, created = Guid.objects.get_or_create(_id=value)
        if created:
            guid.object_id = self.pk
            guid.content_type = ContentType.objects.get_for_model(self)
            guid.save()
        elif guid.content_type == ContentType.objects.get_for_model(self) and guid.object_id == self.pk:
            # TODO should this up the created for the guid until now so that it appears as the first guid
            # for this object?
            return
        else:
            raise InvalidGuid('Cannot indirectly repoint an existing guid, please use the Guid model')

    _primary_key = _id

    @classmethod
    def load(cls, q):
        try:
            queryset = cls.objects.filter(guids___id=q)
            if hasattr(queryset, 'remove_guid_annotations'):
                # Remove annotation then re-annotate
                # doing annotations AFTER the filter allows the
                # JOIN to be reused
                queryset.remove_guid_annotations()
                queryset.annotate_query_with_guids()
            return queryset[0]
        except IndexError:
            # modm doesn't throw exceptions when loading things that don't exist
            return None

    @property
    def deep_url(self):
        return None

    class Meta:
        abstract = True


@receiver(post_save)
def ensure_guid(sender, instance, created, **kwargs):
    if not issubclass(sender, GuidMixin):
        return False
    existing_guids = Guid.objects.filter(object_id=instance.pk, content_type=ContentType.objects.get_for_model(instance))
    has_cached_guids = hasattr(instance, '_prefetched_objects_cache') and 'guids' in instance._prefetched_objects_cache
    if not existing_guids.exists():
        # Clear query cache of instance.guids
        if has_cached_guids:
            del instance._prefetched_objects_cache['guids']
        Guid.objects.create(object_id=instance.pk, content_type=ContentType.objects.get_for_model(instance),
                            _id=generate_guid(instance.__guid_min_length__))
    elif not existing_guids.exists() and instance.guid_string is not None:
        # Clear query cache of instance.guids
        if has_cached_guids:
            del instance._prefetched_objects_cache['guids']
        Guid.objects.create(object_id=instance.pk, content_type_id=instance.content_type_pk,
                            _id=instance.guid_string)
