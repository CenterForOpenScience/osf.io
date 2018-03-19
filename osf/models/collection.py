from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.utils.functional import cached_property
from django.utils import timezone
from include import IncludeManager

from osf.models.base import BaseModel, GuidMixin
from osf.models.validators import validate_title
from osf.utils.fields import NonNaiveDateTimeField
from website.exceptions import NodeStateError
from website.util import api_v2_url

class CollectedGuidMetadata(BaseModel):
    primary_identifier_name = 'guid___id'

    class Meta:
        order_with_respect_to = 'collection'
        unique_together = ('collection', 'guid')

    collection = models.ForeignKey('Collection', on_delete=models.CASCADE)
    guid = models.ForeignKey('Guid', on_delete=models.CASCADE)
    creator = models.ForeignKey('OSFUser')
    collected_type = models.CharField(blank=True, max_length=31)
    status = models.CharField(blank=True, max_length=31)

    @cached_property
    def _id(self):
        return self.guid._id

class Collection(GuidMixin, BaseModel):
    objects = IncludeManager()

    provider = models.ForeignKey('AbstractProvider', blank=True, null=True, on_delete=models.CASCADE)
    creator = models.ForeignKey('OSFUser')
    guid_links = models.ManyToManyField('Guid', through=CollectedGuidMetadata, related_name='collections')
    collected_types = models.ManyToManyField(
        'contenttypes.ContentType',
        related_name='+',
        limit_choices_to={
            'model__in': ['abstractnode', 'basefilenode', 'collection', 'preprintservice']
        })
    title = models.CharField(max_length=200, validators=[validate_title])
    collected_type_choices = ArrayField(models.CharField(max_length=31), blank=True, default=list)
    status_choices = ArrayField(models.CharField(max_length=31), blank=True, default=list)
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
    def linked_nodes_related_url(self):
        return '{}linked_nodes/'.format(self.absolute_api_v2_url)

    @property
    def linked_registrations_related_url(self):
        return '{}linked_registrations/'.format(self.absolute_api_v2_url)

    def save(self, *args, **kwargs):
        first_save = self.id is None
        if self.is_bookmark_collection:
            if first_save and self.creator.collection_set.filter(is_bookmark_collection=True, deleted__isnull=True).exists():
                raise IntegrityError('Each user cannot have more than one Bookmark collection.')
            if self.title != 'Bookmarks':
                # Bookmark collections are always named 'Bookmarks'
                self.title = 'Bookmarks'
        ret = super(Collection, self).save(*args, **kwargs)
        if first_save:
            # Set defaults for M2M
            self.collected_types = ContentType.objects.filter(app_label='osf', model__in=['abstractnode', 'collection'])
        return ret

    def collect_object(self, obj, collector, collected_type=None, status=None):
        """ Adds object to collection, creates CollectedGuidMetadata reference
            Performs type / metadata validation. User permissions checked in view.

        :param GuidMixin obj: Object to collect. Must be of a ContentType specified in collected_types
        :param OSFUser collector: User doing the collecting
        :param str collected_type: Metadata "type" of submission, validated against collected_type_choices
        :param str status: Metadata "status" of submission, validated against status_choices
        :return: CollectedGuidMetadata object or raise exception
        """
        collected_type = collected_type or ''
        status = status or ''

        if self.collected_type_choices and collected_type not in self.collected_type_choices:
            raise ValidationError('"{}" is not an acceptable "type" for this collection'.format(collected_type))

        if self.status_choices and status not in self.status_choices:
            raise ValidationError('"{}" is not an acceptable "status" for this collection'.format(status))

        if not any([isinstance(obj, t.model_class()) for t in self.collected_types.all()]):
            # Not all objects have a content_type_pk, have to look the other way.
            # Ideally, all objects would, and we could do:
            #   self.content_types.filter(id=obj.content_type_pk).exists()
            raise ValidationError('"{}" is not an acceptable "ContentType" for this collection'.format(ContentType.objects.get_for_model(obj).model))

        # Unique together -- self and guid
        if self.collectedguidmetadata_set.filter(guid=obj.guids.first()).exists():
            raise ValidationError('Object already exists in collection.')

        cgm = self.collectedguidmetadata_set.create(guid=obj.guids.first(), creator=collector)
        cgm.collected_type = collected_type
        cgm.status = status
        cgm.save()

        return cgm

    def remove_object(self, obj):
        """ Removes object from collection

        :param obj: object to remove from collection, if it exists. Acceptable types- CollectedGuidMetadata, GuidMixin
        """
        if isinstance(obj, CollectedGuidMetadata):
            if obj.collection == self:
                self.collectedguidmetadata_set.filter(id=obj.id).delete()
                return
        else:
            if self.collectedguidmetadata_set.filter(guid=obj.guids.first()).exists():
                self.collectedguidmetadata_set.filter(guid=obj.guids.first()).delete()
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
        self.save()
