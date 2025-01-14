from collections.abc import Iterable
import logging
import random

import bson
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connections, models
from django.db.models import ForeignKey, UniqueConstraint
from django.db.models.query import QuerySet
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel

from framework import sentry
from osf.exceptions import ValidationError
from osf.utils.caching import cached_property
from osf.utils.fields import LowercaseCharField, NonNaiveDateTimeField
from website import settings as website_settings

ALPHABET = '23456789abcdefghjkmnpqrstuvwxyz'

logger = logging.getLogger(__name__)


def _check_blacklist(guid):
    return BlackListGuid.objects.filter(guid=guid).exists()


def generate_guid(length=5):
    while True:
        guid_id = ''.join(random.sample(ALPHABET, length))

        # is the guid in the blacklist
        if _check_blacklist(guid_id):
            continue

        # it's not, check and see if it's already in the database
        if not Guid.objects.filter(_id=guid_id).exists():
            return guid_id


def generate_object_id():
    return str(bson.ObjectId())


def coerce_guid(maybe_guid, create_if_needed=False):
    if isinstance(maybe_guid, Guid):
        return maybe_guid
    if isinstance(maybe_guid, GuidMixin):
        return maybe_guid.guids.first()
    if isinstance(maybe_guid, OptionalGuidMixin):
        guid = maybe_guid.get_guid(create=create_if_needed)
        if guid is None:
            raise InvalidGuid(f'guid does not exist ({maybe_guid})')
        return guid
    if isinstance(maybe_guid, str):
        guid = Guid.load(maybe_guid)
        if not guid:
            raise InvalidGuid(f'guid does not exist ({maybe_guid})')
        return guid
    raise InvalidGuid(f'cannot coerce {type(maybe_guid)} ({maybe_guid}) into Guid')


def osfid_iri(osfid: str) -> str:
    return ''.join((website_settings.DOMAIN.rstrip('/'), '/', osfid))


class QuerySetExplainMixin:
    def explain(self, *args):
        extra_arguments = ''
        for item in args:
            extra_arguments = f'{extra_arguments} {item}' if isinstance(item, str) else extra_arguments
        cursor = connections[self.db].cursor()
        query, params = self.query.sql_with_params()
        cursor.execute('explain analyze verbose %s' % query, params)
        return '\n'.join(r[0] for r in cursor.fetchall())


QuerySet = type('QuerySet', (QuerySetExplainMixin, QuerySet), dict(QuerySet.__dict__))


class BaseModel(TimeStampedModel, QuerySetExplainMixin):
    migration_page_size = 50000

    objects = models.QuerySet.as_manager()

    class Meta:
        abstract = True

    def __unicode__(self):
        return f'{self.id}'

    def to_storage(self, include_auto_now=True):
        local_django_fields = {x.name for x in self._meta.concrete_fields if
                               include_auto_now or not getattr(x, 'auto_now', False)}
        return {name: self.serializable_value(name) for name in local_django_fields}

    @classmethod
    def get_fk_field_names(cls):
        return [field.name for field in cls._meta.get_fields() if
                field.is_relation and not field.auto_created and (
                field.many_to_one or field.one_to_one) and not isinstance(field, GenericForeignKey)]

    @classmethod
    def get_m2m_field_names(cls):
        return [field.attname or field.name for field in
                cls._meta.get_fields() if
                field.is_relation and field.many_to_many and not hasattr(field, 'field')]

    @classmethod
    def load(cls, data, select_for_update=False):
        try:
            if isinstance(data, str):
                # Some models (CitationStyle) have an _id that is not a bson
                # Looking up things by pk will never work with a str
                return cls.objects.get(_id=data) if not select_for_update else cls.objects.filter(
                    _id=data).select_for_update().get()
            return cls.objects.get(pk=data) if not select_for_update else cls.objects.filter(
                pk=data).select_for_update().get()
        except cls.DoesNotExist:
            return None

    @property
    def _primary_name(self):
        return '_id'

    @property
    def _is_loaded(self):
        return bool(self.pk)

    def reload(self):
        return self.refresh_from_db()

    def refresh_from_db(self, **kwargs):
        super().refresh_from_db(**kwargs)
        # Since Django 2.2, any cached relations are cleared from the reloaded instance.
        # See https://docs.djangoproject.com/en/2.2/ref/models/instances/#django.db.models.Model.refresh_from_db
        # However, the default `refresh_from_db()` doesn't refresh related fields. Neither can we refresh related
        # field(s) since it will inevitably cause infinite loop; and Many/One-to-Many relations add to the complexity.
        # The recommended behavior is to explicitly refresh the fields when necessary. In order to preserve pre-upgrade
        # behavior, our customization only reloads GFKs.
        for f in self._meta._get_fields(reverse=False):
            # Note: the following `if` condition is how django internally identifies GFK
            if f.is_relation and f.many_to_one and not (hasattr(f.remote_field, 'model') and f.remote_field.model):
                if hasattr(self, f.name):
                    try:
                        getattr(self, f.name).refresh_from_db()
                    except AttributeError:
                        continue

    def clone(self):
        """Create a new, unsaved copy of this object."""
        copy = self.__class__.objects.get(pk=self.pk)
        copy.id = None

        # empty all the fks
        fk_field_names = [f.name for f in self._meta.model._meta.get_fields() if
                          isinstance(f, (ForeignKey, GenericForeignKey))]
        for field_name in fk_field_names:
            setattr(copy, field_name, None)

        try:
            copy._id = bson.ObjectId()
        except AttributeError:
            pass
        return copy

    def save(self, *args, **kwargs):
        # Make Django validate on save (like modm)
        if kwargs.pop('clean', True) and not (kwargs.get('force_insert') or kwargs.get('force_update')):
            try:
                self.full_clean()
            except DjangoValidationError as err:
                raise ValidationError(*err.args)
        return super().save(*args, **kwargs)

    def get_semantic_iri(self) -> str:
        '''return the iri that should be consistently used to identify this item
        '''
        raise ValueError(f'no semantic iri for {self} (perhaps implement get_semantic_iri on {self.__class__}?)')

    def get_semantic_iris(self) -> Iterable[str]:
        '''yield iri values that all identify this item (in no particular order)
        '''
        yield from ()  # no semantic iris unless implemented in a subclass


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
    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(null=True, blank=True)

    created = NonNaiveDateTimeField(db_index=True, auto_now_add=True)

    def __repr__(self):
        return f'<id:{self._id}, referent:({self.referent.__repr__()})>'

    @classmethod
    def split_guid(cls, guid_str):
        """Check if the guid str contains version and return a tuple that contains the base guid str and the version.
        """
        if not guid_str:
            return None, None
        guid_parts = guid_str.lower().split(VersionedGuidMixin.GUID_VERSION_DELIMITER)
        base_guid_str = guid_parts[0]
        version = guid_parts[1] if len(guid_parts) > 1 else None
        return base_guid_str, version

    @classmethod
    def load(cls, data, select_for_update=False, ignore_not_found=False):
        """Override load in order to load by Guid.

        Update with versioned Guid: if the guid str stored in data is versioned, only the base guid str is used. This
        is the expected design because base guid str remains a valid one, and it always refers to the latest version.

        If `ignore_not_found` is True, then don't log to sentry. This is used in `website.views.resolve_guid()`.
        """
        if not data:
            return None
        base_guid_str, version = cls.split_guid(data)
        try:
            if not select_for_update:
                return cls.objects.get(_id=base_guid_str)
            return cls.objects.filter(_id=base_guid_str).select_for_update().get()
        except cls.DoesNotExist:
            if not ignore_not_found:
                sentry.log_message(f'Object not found from base guid: '
                                   f'[data={data}, guid={base_guid_str}, version={version}]')
            return None

    @classmethod
    def load_referent(cls, guid_str, ignore_not_found=False):
        """Find and return the referent from a given guid str.
        """
        if not guid_str:
            return None, None
        base_guid_str, version = cls.split_guid(guid_str)
        base_guid_obj = cls.load(base_guid_str, ignore_not_found=ignore_not_found)
        if not base_guid_obj:
            return None, None
        # Handles versioned guid str
        if version:
            if base_guid_obj.is_versioned:
                versioned_obj_qs = base_guid_obj.versions.filter(version=version)
                if not versioned_obj_qs.exists():
                    sentry.log_message(f'Version not found for versioned guid: [guid={base_guid_str}, version={version}]')
                    return None, None
            else:
                sentry.log_message(f'The guid object does not support versioning: [guid={base_guid_str}, version={version}]')
                return None, None
            referent = versioned_obj_qs.first().referent
            return referent, referent.version
        # Handles guid str without version
        referent = base_guid_obj.referent
        # If the guid str doesn't have version but supports versioning, we need to check and return the version
        version = referent.version if hasattr(referent, 'version') else None
        return referent, version

    @property
    def is_versioned(self):
        return self.versions.exists()

    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'
        index_together = (
            ('content_type', 'object_id', 'created'),
        )


class GuidVersionsThrough(BaseModel):
    """Stores versions of versioned guid obj. It refers to both the versioned obj (referent) and the base guid obj.
    """

    created = NonNaiveDateTimeField(db_index=True, auto_now_add=True)
    referent = GenericForeignKey()
    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    guid = models.ForeignKey('Guid', related_name='versions', on_delete=models.CASCADE)
    version = models.PositiveIntegerField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['guid', 'version'], name='unique_guid_version')
        ]


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
        return f'_id: {self._id}'

    @classmethod
    def load(cls, q, select_for_update=False):
        try:
            return cls.objects.get(_id=q) if not select_for_update else cls.objects.filter(
                _id=q).select_for_update().get()
        except cls.DoesNotExist:
            # modm doesn't throw exceptions when loading things that don't exist
            return None

    class Meta:
        abstract = True


class TypedObjectIDMixin(ObjectIDMixin):
    class Meta:
        abstract = True
        # On subclasses, be sure to add a unique_together constraint on '_id' and 'type'

    _id = models.CharField(max_length=24, default=generate_object_id, db_index=True)

    @classmethod
    def load(cls, q, select_for_update=False):
        try:
            return cls.objects.get(_id=q, type=cls._typedmodels_type) if not select_for_update else cls.objects.filter(
                _id=q, type=cls._typedmodels_type).select_for_update().get()
        except cls.DoesNotExist:
            # modm doesn't throw exceptions when loading things that don't exist
            return None
        except AttributeError as e:
            # load has been called on an Abstract typed class
            e.message = f'"load" must be called on a typed class, got {cls.__name__}'
            raise


class InvalidGuid(Exception):
    pass


class OptionalGuidMixin(BaseIDMixin):
    """
    This makes it so that things can **optionally** have guids. Think files.
    Things that inherit from this must also inherit from ObjectIDMixin ... probably
    """
    __guid_min_length__ = 5

    guids = GenericRelation(Guid, related_name='referent', related_query_name='referents')
    content_type_pk = models.PositiveIntegerField(null=True, blank=True)

    def __unicode__(self):
        return f'{self.get_guid() or self.id}'

    def get_guid(self, create=False):
        if not self.pk:
            logger.warning('Implicitly saving object before creating guid')
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
        return self.guids.first()

    def get_semantic_iri(self) -> str:
        _osfid = self.get_guid()
        if not _osfid:
            raise ValueError(f'no osfid for {self} (cannot build semantic iri)')
        return osfid_iri(_osfid._id)

    def get_semantic_iris(self) -> Iterable[str]:
        try:  # since this is a mixin, don't assume osf.models.BaseModel
            _get_super_iris = super().get_semantic_iris
        except AttributeError:
            pass
        else:
            yield from _get_super_iris()
        # yield iri for each guid
        for _osfid in self.guids.all():
            yield osfid_iri(_osfid._id)

    class Meta:
        abstract = True


class GuidMixinQuerySet(QuerySet):

    def _filter_or_exclude(self, negate, *args, **kwargs):
        return super()._filter_or_exclude(
            negate,
            *args,
            **kwargs
        ).prefetch_related('guids')

    def all(self):
        if self._fields:
            return super().all()
        return super().all().prefetch_related('guids')


class GuidMixin(BaseIDMixin):
    __guid_min_length__ = 5

    guids = GenericRelation(Guid, related_name='referent', related_query_name='referents')
    content_type_pk = models.PositiveIntegerField(null=True, blank=True)

    objects = GuidMixinQuerySet.as_manager()

    # TODO: use pre-delete signal to disable delete cascade

    def __unicode__(self):
        return f'{self._id}'

    @cached_property
    def _id(self):
        try:
            guid = self.guids.first()
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
    def load(cls, q, select_for_update=False):
        # Minor optimization--no need to query if q is None or ''
        if not q:
            return None
        try:
            # guids___id__isnull=False forces an INNER JOIN
            if select_for_update:
                return cls.objects.filter(guids___id__isnull=False, guids___id=q).select_for_update()[:1].get()
            return cls.objects.filter(guids___id__isnull=False, guids___id=q)[:1].get()
        except cls.DoesNotExist:
            return None

    @property
    def deep_url(self):
        return None

    def get_semantic_iri(self) -> str:
        _osfid = self._id
        if not _osfid:
            raise ValueError(f'no osfid for {self} (cannot build semantic iri)')
        return osfid_iri(_osfid)

    def get_semantic_iris(self) -> Iterable[str]:
        try:  # since this is a mixin, don't assume osf.models.BaseModel
            _get_super_iris = super().get_semantic_iris
        except AttributeError:
            pass
        else:
            yield from _get_super_iris()
        # yield iri for each guid
        for _osfid in self.guids.all():
            yield osfid_iri(_osfid._id)

    class Meta:
        abstract = True


class VersionedGuidMixin(GuidMixin):
    """Inherits from `GuidMixin` to support objects that use the `GuidVersionsThrough` table for versioning.
    """

    class Meta:
        abstract = True

    INITIAL_VERSION_NUMBER = 1
    GUID_VERSION_DELIMITER = '_v'

    versioned_guids = GenericRelation('GuidVersionsThrough', related_name='referent', related_query_name='referents')

    @cached_property
    def _id(self):
        try:
            versioned_guid = self.versioned_guids
            if not versioned_guid.exists():
                # This can happen during the gap AFTER preprint version is created and BEFORE versioned guid is created.
                # This happens every time recursively inside `.super().save()` when the `preprint.save()` is called for
                # the first time during preprint creation and new preprint version creation.
                sentry.log_message(
                    f'`self.versioned_guids` does not exist: [self={self.pk}, type={type(self).__name__}]'
                )
                return None
            guid = versioned_guid.first().guid
            version = versioned_guid.first().version
        except IndexError as e:
            sentry.log_exception(e)
            return None
        return f'{guid._id}{VersionedGuidMixin.GUID_VERSION_DELIMITER}{version}'

    @_id.setter
    def _id(self, value):
        # TODO: should we enable setter for `_id`, which we found some usage in unit tests
        pass

    _primary_key = _id

    @cached_property
    def version(self):
        # Once assigned, version number never changes
        return self.versioned_guids.first().version

    @classmethod
    def load(cls, guid_str, select_for_update=False):
        """Override load in order to load by Versioned Guid. It finds and returns the versioned object based on the
        base guid str and the version in the guid str. If the guid str does not have version, it returns the object
        referred by the base guid obj.
        """
        if not guid_str:
            return None
        try:
            base_guid_str, version = Guid.split_guid(guid_str)
            # Version exists
            if version:
                if not select_for_update:
                    return cls.objects.get(versioned_guids__guid___id=base_guid_str, versioned_guids__version=version)
                return cls.objects.filter(
                    versioned_guids__guid___id=base_guid_str,
                    versioned_guids__version=version
                ).select_for_update().get()
            # Version does not exists
            if not select_for_update:
                return cls.objects.filter(guids___id=base_guid_str).first()
            return cls.objects.filter(guids___id=guid_str).select_for_update().get()
        except cls.DoesNotExist:
            sentry.log_message(f'Object not found for VersionedGuidMixin: [guid_str={guid_str}]')
            return None
        except cls.MultipleObjectsReturned:
            return None

    def get_guid(self):
        """A helper for getting the base guid
        """
        return self.versioned_guids.first().guid

    def get_semantic_iri(self):
        """Override `get_semantic_iri()` in `GuidMixin` so that all versions of the same object have the same semantic
        iri using only the base guid str.
        """
        _osfid = self.get_guid()._id
        if not _osfid:
            raise ValueError(f'no osfid for {self} (cannot build semantic iri)')
        return osfid_iri(_osfid)

    def update_search(self, skip_share=False):
        """Subclasses must implement `update_search()` with kwarg `skip_share=False`."""
        raise NotImplementedError()

@receiver(post_save)
def ensure_guid(sender, instance, **kwargs):
    """Generate guid if it doesn't exist for subclasses of GuidMixin except for subclasses of VersionedGuidMixin

    Note: must have **kwargs though not used since signal receivers must accept keyword arguments.
    """
    if not issubclass(sender, GuidMixin):
        return False
    if issubclass(sender, VersionedGuidMixin):
        # For classes that support version using VersionedGuidMixin, the base guid object must be generated manually.
        # Only the initial or the latest version is referred to by the base guid in the Guid table. All versions have
        # their "versioned" guid in the GuidVersionsThrough table.
        return False
    existing_guids = Guid.objects.filter(
        object_id=instance.pk,
        content_type=ContentType.objects.get_for_model(instance)
    )
    has_cached_guids = hasattr(instance, '_prefetched_objects_cache') and 'guids' in instance._prefetched_objects_cache
    if not existing_guids.exists():
        # Clear query cache of instance.guids
        if has_cached_guids:
            del instance._prefetched_objects_cache['guids']
        Guid.objects.create(
            object_id=instance.pk,
            content_type=ContentType.objects.get_for_model(instance),
            _id=generate_guid(instance.__guid_min_length__)
        )
