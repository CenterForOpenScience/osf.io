import logging

from dirtyfields import DirtyFieldsMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.utils.functional import cached_property
from django.utils import timezone
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from include import IncludeManager
from framework.celery_tasks.handlers import enqueue_task

from osf.models.base import BaseModel, GuidMixin
from osf.models.mixins import GuardianMixin, TaxonomizableMixin
from osf.models.validators import validate_title
from osf.utils.fields import NonNaiveDateTimeField
from osf.exceptions import NodeStateError
from website.util import api_v2_url
from website.search.exceptions import SearchUnavailableError

logger = logging.getLogger(__name__)

class CollectionSubmission(TaxonomizableMixin, BaseModel):
    primary_identifier_name = 'guid___id'

    class Meta:
        order_with_respect_to = 'collection'
        unique_together = ('collection', 'guid')

    collection = models.ForeignKey('Collection', on_delete=models.CASCADE)
    guid = models.ForeignKey('Guid', on_delete=models.CASCADE)
    creator = models.ForeignKey('OSFUser')
    collected_type = models.CharField(blank=True, max_length=127)
    status = models.CharField(blank=True, max_length=127)
    volume = models.CharField(blank=True, max_length=127)
    issue = models.CharField(blank=True, max_length=127)
    program_area = models.CharField(blank=True, max_length=127)

    @cached_property
    def _id(self):
        return '{}-{}'.format(self.guid._id, self.collection._id)

    @classmethod
    def load(cls, data, select_for_update=False):
        try:
            cgm_id, collection_id = data.split('-')
        except ValueError:
            raise ValueError('Invalid CollectionSubmission object <_id {}>'.format(data))
        else:
            if cgm_id and collection_id:
                try:
                    if isinstance(data, str):
                        return (cls.objects.get(guid___id=cgm_id, collection__guids___id=collection_id) if not select_for_update
                                else cls.objects.filter(guid___id=cgm_id, collection__guids___id=collection_id).select_for_update().get())
                except cls.DoesNotExist:
                    return None
            return None

    def update_index(self):
        if self.collection.is_public:
            from website.search.search import update_collected_metadata
            try:
                update_collected_metadata(self.guid._id, collection_id=self.collection.id)
            except SearchUnavailableError as e:
                logger.exception(e)

    def remove_from_index(self):
        from website.search.search import update_collected_metadata
        try:
            update_collected_metadata(self.guid._id, collection_id=self.collection.id, op='delete')
        except SearchUnavailableError as e:
            logger.exception(e)

    def save(self, *args, **kwargs):
        kwargs.pop('old_subjects', None)  # Not indexing this, trash it
        ret = super(CollectionSubmission, self).save(*args, **kwargs)
        self.update_index()
        return ret

class Collection(DirtyFieldsMixin, GuidMixin, BaseModel, GuardianMixin):
    objects = IncludeManager()

    groups = {
        'read': ('read_collection', ),
        'write': ('read_collection', 'write_collection', ),
        'admin': ('read_collection', 'write_collection', 'admin_collection', )
    }
    group_format = 'collections_{self.id}_{group}'

    class Meta:
        permissions = (
            ('read_collection', 'Read Collection'),
            ('write_collection', 'Write Collection'),
            ('admin_collection', 'Admin Collection'),
        )

    provider = models.ForeignKey('AbstractProvider', blank=True, null=True, on_delete=models.CASCADE)
    creator = models.ForeignKey('OSFUser')
    guid_links = models.ManyToManyField('Guid', through=CollectionSubmission, related_name='collections')
    collected_types = models.ManyToManyField(
        'contenttypes.ContentType',
        related_name='+',
        limit_choices_to={
            'model__in': ['abstractnode', 'basefilenode', 'collection', 'preprint']
        })
    title = models.CharField(max_length=200, validators=[validate_title])
    collected_type_choices = ArrayField(models.CharField(max_length=127), blank=True, default=list)
    status_choices = ArrayField(models.CharField(max_length=127), blank=True, default=list)
    volume_choices = ArrayField(models.CharField(max_length=127), blank=True, default=list)
    issue_choices = ArrayField(models.CharField(max_length=127), blank=True, default=list)
    program_area_choices = ArrayField(models.CharField(max_length=127), blank=True, default=list)
    is_public = models.BooleanField(default=False, db_index=True)
    is_promoted = models.BooleanField(default=False, db_index=True)
    is_bookmark_collection = models.BooleanField(default=False, db_index=True)
    deleted = NonNaiveDateTimeField(null=True, blank=True)

    def __unicode__(self):
        return '{self.title!r}, with guid {self._id!r}'.format(self=self)

    @property
    def url(self):
        return '/{}/'.format(self._id)

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    @property
    def absolute_api_v2_url(self):
        return api_v2_url('/collections{}'.format(self.url))

    @property
    def linked_nodes_self_url(self):
        return '{}relationships/linked_nodes/'.format(self.absolute_api_v2_url)

    @property
    def linked_registrations_self_url(self):
        return '{}relationships/linked_registrations/'.format(self.absolute_api_v2_url)

    @property
    def linked_preprints_self_url(self):
        return '{}relationships/linked_preprints/'.format(self.absolute_api_v2_url)

    @property
    def linked_preprints_related_url(self):
        return '{}linked_preprints/'.format(self.absolute_api_v2_url)

    @property
    def linked_nodes_related_url(self):
        return '{}linked_nodes/'.format(self.absolute_api_v2_url)

    @property
    def linked_registrations_related_url(self):
        return '{}linked_registrations/'.format(self.absolute_api_v2_url)

    @classmethod
    def bulk_update_search(cls, cgms, op='update', index=None):
        from website import search
        try:
            search.search.bulk_update_collected_metadata(cgms, op=op, index=index)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)

    def save(self, *args, **kwargs):
        first_save = self.id is None
        if self.is_bookmark_collection:
            if first_save and self.creator.collection_set.filter(is_bookmark_collection=True, deleted__isnull=True).exists():
                raise IntegrityError('Each user cannot have more than one Bookmark collection.')
            if self.title != 'Bookmarks':
                # Bookmark collections are always named 'Bookmarks'
                self.title = 'Bookmarks'
        saved_fields = self.get_dirty_fields() or []
        ret = super(Collection, self).save(*args, **kwargs)

        if first_save:
            # Set defaults for M2M
            self.collected_types = ContentType.objects.filter(app_label='osf', model__in=['abstractnode', 'collection', 'preprint'])
            # Set up initial permissions
            self.update_group_permissions()
            self.get_group('admin').user_set.add(self.creator)

        elif 'is_public' in saved_fields:
            from website.collections.tasks import on_collection_updated
            enqueue_task(on_collection_updated.s(self._id))

        return ret

    def has_permission(self, user, perm):
        return user.has_perms(self.groups[perm], self)

    def collect_object(self, obj, collector, collected_type=None, status=None, volume=None, issue=None, program_area=None):
        """ Adds object to collection, creates CollectionSubmission reference
            Performs type / metadata validation. User permissions checked in view.

        :param GuidMixin obj: Object to collect. Must be of a ContentType specified in collected_types
        :param OSFUser collector: User doing the collecting
        :param str collected_type: Metadata "type" of submission, validated against collected_type_choices
        :param str status: Metadata "status" of submission, validated against status_choices
        :return: CollectionSubmission object or raise exception
        """
        collected_type = collected_type or ''
        status = status or ''
        volume = volume or ''
        issue = issue or ''
        program_area = program_area or ''

        if not self.collected_type_choices and collected_type:
            raise ValidationError('May not specify "type" for this collection')

        if not self.status_choices and status:
            raise ValidationError('May not specify "status" for this collection')

        if not self.volume_choices and volume:
            raise ValidationError('May not specify "volume" for this collection')

        if not self.issue_choices and issue:
            raise ValidationError('May not specify "issue" for this collection')

        if not self.program_area_choices and program_area:
            raise ValidationError('May not specify "program_area" for this collection')

        if self.collected_type_choices and collected_type not in self.collected_type_choices:
            raise ValidationError('"{}" is not an acceptable "type" for this collection'.format(collected_type))

        if self.status_choices and status not in self.status_choices:
            raise ValidationError('"{}" is not an acceptable "status" for this collection'.format(status))

        if self.volume_choices and volume not in self.volume_choices:
            raise ValidationError('"{}" is not an acceptable "volume" for this collection'.format(volume))

        if self.issue_choices and issue not in self.issue_choices:
            raise ValidationError('"{}" is not an acceptable "issue" for this collection'.format(issue))

        if self.program_area_choices and program_area not in self.program_area_choices:
            raise ValidationError('"{}" is not an acceptable "program_area" for this collection'.format(program_area))

        if not any([isinstance(obj, t.model_class()) for t in self.collected_types.all()]):
            # Not all objects have a content_type_pk, have to look the other way.
            # Ideally, all objects would, and we could do:
            #   self.content_types.filter(id=obj.content_type_pk).exists()
            raise ValidationError('"{}" is not an acceptable "ContentType" for this collection'.format(ContentType.objects.get_for_model(obj).model))

        # Unique together -- self and guid
        if self.collectionsubmission_set.filter(guid=obj.guids.first()).exists():
            raise ValidationError('Object already exists in collection.')

        cgm = self.collectionsubmission_set.create(guid=obj.guids.first(), creator=collector)
        cgm.collected_type = collected_type
        cgm.status = status
        cgm.volume = volume
        cgm.issue = issue
        cgm.program_area = program_area
        cgm.save()

        return cgm

    def remove_object(self, obj):
        """ Removes object from collection

        :param obj: object to remove from collection, if it exists. Acceptable types- CollectionSubmission, GuidMixin
        """
        if isinstance(obj, CollectionSubmission):
            if obj.collection == self:
                obj.remove_from_index()
                self.collectionsubmission_set.filter(id=obj.id).delete()
                return
        else:
            cgm = self.collectionsubmission_set.get(guid=obj.guids.first())
            if cgm:
                cgm.remove_from_index()
                cgm.delete()
                return
        raise ValueError('Node link does not belong to the requested node.')

    def delete(self):
        """ Mark collection as deleted
        """
        if self.is_bookmark_collection:
            # Not really the right exception to raise, but it's for back-compatibility
            # TODO: Use a more correct exception and catch it in the necessary places
            raise NodeStateError('Bookmark collections may not be deleted.')

        self.deleted = timezone.now()

        if self.is_public:
            self.bulk_update_search(list(self.collectionsubmission_set.all()), op='delete')

        self.save()


class CollectionUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Collection, on_delete=models.CASCADE)


class CollectionGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Collection, on_delete=models.CASCADE)
