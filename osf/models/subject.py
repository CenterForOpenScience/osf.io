# -*- coding: utf-8 -*-
from dirtyfields import DirtyFieldsMixin
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from include import IncludeQuerySet

from website.util import api_v2_url

from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.validators import validate_subject_hierarchy_length, validate_subject_provider_mapping, validate_subject_highlighted_count

class SubjectQuerySet(IncludeQuerySet):
    def include_children(self):
        # It would be more efficient to OR self with the latter two Q's,
        # but this breaks for certain querysets when relabeling aliases.
        return Subject.objects.filter(Q(id__in=self.values_list('id', flat=True)) | Q(parent__in=self) | Q(parent__parent__in=self))

class Subject(ObjectIDMixin, BaseModel, DirtyFieldsMixin):
    """A subject discipline that may be attached to a preprint."""

    text = models.CharField(null=False, max_length=256, db_index=True)  # max length on prod: 73
    parent = models.ForeignKey('self', related_name='children', null=True, blank=True, on_delete=models.SET_NULL, validators=[validate_subject_hierarchy_length])
    bepress_subject = models.ForeignKey('self', related_name='aliases', null=True, blank=True, on_delete=models.deletion.CASCADE)
    provider = models.ForeignKey('AbstractProvider', related_name='subjects', on_delete=models.deletion.CASCADE)
    highlighted = models.BooleanField(db_index=True, default=False)

    objects = SubjectQuerySet.as_manager()

    class Meta:
        base_manager_name = 'objects'
        unique_together = ('text', 'provider')
        permissions = (
            ('view_subject', 'Can view subject details'),
        )

    def __unicode__(self):
        return '{} with id {}'.format(self.text, self.id)

    @property
    def absolute_api_v2_url(self):
        return api_v2_url('taxonomies/{}/'.format(self._id))

    @property
    def child_count(self):
        """For v1 compat."""
        return self.children.count()

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    @cached_property
    def path(self):
        return '{}|{}'.format(self.provider.share_title, '|'.join([s.text for s in self.object_hierarchy]))

    @cached_property
    def bepress_text(self):
        if self.bepress_subject:
            return self.bepress_subject.text
        return self.text

    @cached_property
    def hierarchy(self):
        if self.parent:
            return self.parent.hierarchy + [self._id]
        return [self._id]

    @cached_property
    def object_hierarchy(self):
        if self.parent:
            return self.parent.object_hierarchy + [self]
        return [self]

    def save(self, *args, **kwargs):
        saved_fields = self.get_dirty_fields() or []
        validate_subject_provider_mapping(self.provider, self.bepress_subject)
        validate_subject_highlighted_count(self.provider, bool('highlighted' in saved_fields and self.highlighted))
        if 'text' in saved_fields and self.pk and (self.preprintservices.exists() or self.abstractnodes.exists()):
            raise ValidationError('Cannot edit a used Subject')
        return super(Subject, self).save()

    def delete(self, *args, **kwargs):
        if self.preprintservices.exists() or self.abstractnodes.exists():
            raise ValidationError('Cannot delete a used Subject')
        return super(Subject, self).delete()
